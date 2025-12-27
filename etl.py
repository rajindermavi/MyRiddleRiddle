from download_podcasts import download_podcasts
from config import (
    RSS_FEED, 
    STG_1_DIR,
    STG_1_META,
    STG_2_DIR,
    STG_2_META
)

dl_pod_config = {
    'start_date':None,
    'end_date':None,
    'limit':3,
    'output_dir': STG_1_DIR,
    'metadata_file':STG_1_META,
    'sort_order':'asc',
}

def etl(rss_url):
    download_podcasts(rss_url,**dl_pod_config)

if __name__ == '__main__':
    etl(RSS_FEED)

