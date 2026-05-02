from io import BytesIO
import logging
import zulip
import requests
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():

    stream_id = 595147
    client = zulip.Client(config_file="zuliprc")
    topics = client.get_stream_topics(stream_id)
    today = datetime.today().date()
    topic_name = f"Comic for {today}"

    topics_set = set(t['name'] for t in topics['topics'])
    if topic_name in topics_set:
       logger.error("Today's comic already posted. Aborting.")
       return
       
    page = requests.get("https://www.creators.com/read/heathcliff").text
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
        return
    datetime_object = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
    date_object = datetime_object.date()

    if not today == date_object:
        logger.warning("Today's comic not available!")
        return

    data = BytesIO(requests.get(image_url).content)


    data.name = f"comic_{date_object}.jpg"

    result = client.upload_file(data)
    client.send_message(
        {
            "type": "channel",
            "to": stream_id,
            "topic": topic_name,
            "content": "Today's [Heathcliff]({})".format(result["url"]),
        }
    )
    logger.info("Sent comic for %s", date_object)

if __name__ == "__main__":
    main()
