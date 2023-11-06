import os.path
import time
from enum import Enum
import json
import pandas as pd
import requests
import multiprocessing


class RetryTypes(str, Enum):
    store = "store"
    status = "status"
    timezone = "timezone"
    business_hour = "business-hour"


def send_requests_with_processes(reqs, send_request):
    processes = []
    for req in reqs:
        process = multiprocessing.Process(target=send_request, args=(*req,))
        processes.append(process)
        process.start()
    for process in processes:
        process.join()


class DummyData:
    def __init__(self):
        self.store_status_csv_path = os.path.abspath('store-status.csv')
        self.timezones_csv_path = os.path.abspath('timezones.csv')
        self.menu_hours_csv_path = os.path.abspath('menu-hours.csv')
        self.retry_list_path = os.path.abspath('retry-list.json')
        self.host = 'http://localhost:8000'
        # updates that failed and should be retried.
        self.retry_list = []  # {"index": int, "data": obj, "type": "store" or "store-status" etc}

    def create_store(self, row_index: int, store_id: str):
        payload = {'store_id': store_id}
        create_store_endpoint = f"{self.host}/store"

        try:
            response = requests.post(create_store_endpoint, json=payload)
            response.raise_for_status()
            print(f"{row_index + 1} Successfully created store with store_id {store_id}")
        except requests.exceptions.RequestException as e:
            print(f"Error processing store_id {store_id}: {str(e)}")
            self.add_to_retry_list({"index": row_index, "data": payload, "type": RetryTypes.store.value})

    def add_to_retry_list(self, item: dict):
        self.retry_list.append(item)

    def create_record(self, row_index: int, data: dict, _type: RetryTypes, endpoint: str):
        payload = {**data}
        try:
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            print(f"{row_index + 1} Successfully created record type {_type.value} with store_id {data['store_id']}")
        except requests.exceptions.RequestException as e:
            print(f"Error processing store_id {data['store_id']}: {str(e)}")
            self.add_to_retry_list({"index": row_index, "data": payload, "type": _type.value})

    def populate_stores(self):
        start_time = time.time()
        store_statuses = pd.read_csv(self.store_status_csv_path, names=['store_id', 'status', 'timestamp_utc'])
        # stores have whitespaces causing the extra duplicates to show up.
        store_ids = store_statuses['store_id'].str.strip()
        # removing all duplicates returns the unique stores in our dataset.
        store_ids = pd.Series(store_ids).drop_duplicates()

        for index, store_id in enumerate(store_ids):
            if index == 0:
                continue
            self.create_store(index, store_id=store_id)

        end_time = time.time()
        print("Processing completed.")
        print(f"took {end_time - start_time} seconds.")

    # chunk_size = 100
    # for chunk in pd.read_csv(self.store_status_csv_path, chunksize=chunk_size,
    #                          names=['store_id', 'status', 'timestamp_utc']):
    #     for index, row in chunk.iterrows():
    #         if index == 0:
    #             continue
    #         store_id: str = row['store_id']
    #         self.create_store(index, store_id=store_id)
    #
    # end_time = time.time()
    # print("Processing completed.")
    # print(f"took {end_time - start_time} seconds.")

    def populate_status_polls(self, limit: int = 100):
        endpoint = f"{self.host}/store-status"
        start_time = time.time()
        chunk_size = 20
        for chunk in pd.read_csv(self.store_status_csv_path, chunksize=chunk_size,
                                 names=['store_id', 'status', 'timestamp_utc']):
            reqs = []
            for index, row in chunk.iterrows():
                if index == 0:
                    continue
                if index == limit:
                    print(f"took {time.time() - start_time} seconds.")
                    exit(0)

                store_id: str = row['store_id']

                timestamp_utc: str = row['timestamp_utc']
                timestamp_value = timestamp_utc.rsplit(" UTC")[0]
                # some timestamps have a fractional value less than 6 digits which is not supported by the iso-format
                # parser.
                min_iso_fraction_len = 6
                fractions_length = len(timestamp_value.rsplit(".").pop())
                if fractions_length < min_iso_fraction_len:
                    padding = "0" * (min_iso_fraction_len - fractions_length)
                    timestamp_value += padding

                utc_datetime: str = timestamp_value + "+00:00"

                status: str = row['status']
                payload = {'store_id': store_id, 'timestamp_utc': utc_datetime, 'status': status}
                reqs.append((index, payload, RetryTypes.status, endpoint))
            send_requests_with_processes(reqs, self.create_record)

        end_time = time.time()
        print("Processing completed.")
        print(f"took {end_time - start_time} seconds.")
        print(f"saving retry list...")
        with open(self.retry_list_path, 'w') as file:
            json.dump(self.retry_list, file, indent=4)

        print(f"retry list saved to {self.retry_list_path}")

    def populate_timezones(self):
        endpoint = f"{self.host}/timezone"
        start_time = time.time()
        chunk_size = 20
        for chunk in pd.read_csv(self.timezones_csv_path, chunksize=chunk_size,
                                 names=['store_id', 'timezone_str']):
            reqs = []
            for index, row in chunk.iterrows():
                if index == 0:
                    continue

                store_id: str = row['store_id']
                timezone_str: str = row['timezone_str']
                payload = {'store_id': store_id, 'timezone_str': timezone_str}
                reqs.append((index, payload, RetryTypes.timezone, endpoint))
            send_requests_with_processes(reqs, self.create_record)

        end_time = time.time()
        print("Processing completed.")
        print(f"took {end_time - start_time} seconds.")
        print(f"saving retry list...")
        with open(self.retry_list_path, 'w') as file:
            json.dump(self.retry_list, file, indent=4)

        print(f"retry list saved to {self.retry_list_path}")

    def populate_business_hours(self):
        endpoint = f"{self.host}/business-hours"
        start_time = time.time()
        chunk_size = 20
        for chunk in pd.read_csv(self.menu_hours_csv_path, chunksize=chunk_size,
                                 names=['store_id', 'day', 'start_time_local', 'end_time_local']):
            reqs = []
            for index, row in chunk.iterrows():
                if index == 0:
                    continue

                store_id: str = row['store_id']
                day: str = row['day']
                start_time_local: str = row['start_time_local']
                end_time_local: str = row['end_time_local']
                payload = {
                    'store_id': store_id,
                    'day_of_week': day,
                    'start_time_local': start_time_local,
                    'end_time_local': end_time_local,
                }
                reqs.append((index, payload, RetryTypes.business_hour, endpoint))
            send_requests_with_processes(reqs, self.create_record)

        end_time = time.time()
        print("Processing completed.")
        print(f"took {end_time - start_time} seconds.")
        print(f"saving retry list...")
        with open(self.retry_list_path, 'w') as file:
            json.dump(self.retry_list, file, indent=4)

        print(f"retry list saved to {self.retry_list_path}")


if __name__ == "__main__":
    dummy_data = DummyData()
    dummy_data.populate_stores()
    dummy_data.populate_timezones()
    dummy_data.populate_business_hours()
    dummy_data.populate_status_polls(limit=100000)
