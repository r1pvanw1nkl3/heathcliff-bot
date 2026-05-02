from io import BytesIO
import logging
import sys
import zulip
import requests
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():

    stream_id = 595147
    client = zulip.Client(config_file="zuliprc")

    try:
        topics = client.get_stream_topics(stream_id)
    except Exception as e:
        logger.error("Failed to fetch stream topics: %s", e)
        sys.exit(1)

    today = datetime.today().date()
    topic_name = f"Comic for {today}"

    topics_set = set(t['name'] for t in topics['topics'])
    if topic_name in topics_set:
       logger.error("Today's comic already posted. Aborting.")
       return

    try:
        page = requests.get("https://www.creators.com/read/heathcliff", timeout=30).text
    except requests.RequestException as e:
        logger.error("Failed to fetch comic page: %s", e)
        sys.exit(1)

    soup = BeautifulSoup(page, "html.parser")

    metas = soup.find_all("meta")

    image_url = None
    datetime_str = None
    for m in metas:
        property = m.get("property")
        if property:
            if property == "og:image":
                image_url = m['content']
            elif property == "article:published_time":
                datetime_str = m['content']
    if not image_url or not datetime_str or not isinstance(datetime_str, str):
        logger.error("URL or Date not found.")
        sys.exit(1)

    datetime_object = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
    date_object = datetime_object.date()

    if not today == date_object:
        logger.warning("Today's comic not available!")
        return

    try:
        data = BytesIO(requests.get(image_url, timeout=30).content)
    except requests.RequestException as e:
        logger.error("Failed to download comic image: %s", e)
        sys.exit(1)

    data.name = f"comic_{date_object}.jpg"

    try:
        result = client.upload_file(data)
        client.send_message(
            {
                "type": "channel",
                "to": stream_id,
                "topic": topic_name,
                "content": "Today's [Heathcliff]({})".format(result["url"]),
            }
        )
    except Exception as e:
        logger.error("Failed to upload/send to Zulip: %s", e)
        sys.exit(1)

    logger.info("Sent comic for %s", date_object)

if __name__ == "__main__":
    main()
