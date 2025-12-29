from etl.download_podcasts import download_podcasts
from etl.transcribe_podcasts import transcribe_podcasts
from config import (
    RSS_FEED,
    STG_1_DIR,
    STG_1_META,
    STG_2_DIR,
    STG_2_META
)

download_podcasts_config = {
    'start_date': None,
    'end_date': None,
    'limit': 10,
    'output_dir': STG_1_DIR,
    'metadata_file': STG_1_META,
    'sort_order': 'asc',
}

transcribe_podcasts_config = {
    'metadata_path': STG_1_META,
    'output_dir': STG_2_DIR,
    'output_metadata_path': STG_2_META,
}

def etl(rss_url):
    # Stage 1: Download podcasts
    print("=" * 60)
    print("STAGE 1: Downloading podcasts")
    print("=" * 60)
    download_podcasts(rss_url, **download_podcasts_config)

    # Stage 2: Transcribe podcasts
    print("\n" + "=" * 60)
    print("STAGE 2: Transcribing podcasts")
    print("=" * 60)
    transcribe_podcasts(**transcribe_podcasts_config)

    print("\n" + "=" * 60)
    print("ETL PIPELINE COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    etl(RSS_FEED)

