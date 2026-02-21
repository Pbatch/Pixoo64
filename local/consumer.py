import json
import time

from parkrun import Parkrun
from pixoo import Pixoo
from tfl import ID_TO_STATION, TFL, Stations

pixoo = Pixoo()
tfl = TFL()
parkrun = Parkrun()


def lambda_handler(event, context):
    record = event["Records"][0]
    body = json.loads(record["body"])
    mode = body["mode"]

    if mode == "tfl":
        station = ID_TO_STATION[body["station_id"]]
        inbound = body["inbound"]

        image = tfl.make_image(
            arrivals=tfl.get_and_filter_arrivals(station.station_id, inbound),
            header_text=station.nickname.capitalize(),
            underground=station.underground,
        )
    elif mode == "parkrun":
        id_to_name = body["id_to_name"]
        image = parkrun.make_image(id_to_name)
    else:
        raise ValueError(f'Mode "{mode}" is not supported')

    payload = {
        "Command": "Draw/SendHttpGif",
        "PicNum": 1,
        "PicWidth": 64,
        "PicOffset": 0,
        "PicID": int(time.time()),
        "PicSpeed": 0,
        "PicData": pixoo.encode_image(image),
    }
    result = pixoo.post(payload)

    return result


def main():
    body = {
        "mode": "tfl",
        "station_id": Stations.HAMPSTEAD_HEATH.station_id,
        "inbound": True,
    }
    event = {"Records": [{"body": json.dumps(body)}]}
    context = None
    result = lambda_handler(event, context)
    print(result)


if __name__ == "__main__":
    main()
