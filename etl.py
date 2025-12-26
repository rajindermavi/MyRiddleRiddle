from download_podcasts import download_podcasts
from config import rss_feed, dl_pod_config

def etl(rss_url):
    download_podcasts(rss_url,**dl_pod_config)

if __name__ == '__main__':
    etl(rss_feed)

