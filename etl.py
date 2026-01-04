from etl.download_podcasts import download_podcasts
from etl.transcribe_podcasts import transcribe_podcasts
from etl.diarize_podcast import diarize_podcasts
from config import (
    RSS_FEED,
    STG_1_DIR,
    STG_1_META,
    STG_2_DIR,
    STG_2_META,
    STG_3_DIR,
    STG_3_META,
    STG_4_DIR,
    STG_4_META
)

from utilities.logging import get_logger

logger = get_logger()

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

diarize_podcasts_config = {
    'metadata_path': STG_2_META,
    'output_dir': STG_3_DIR,
    'output_metadata_path': STG_3_META,
}

def etl(rss_url):
    # Stage 1: Download podcasts
    logger("=" * 60)
    logger("STAGE 1: Downloading podcasts")
    logger("=" * 60)
    download_podcasts(rss_url, **download_podcasts_config)

    # Stage 2: Transcribe podcasts
    logger("\n" + "=" * 60)
    logger("STAGE 2: Transcribing podcasts")
    logger("=" * 60)
    transcribe_podcasts(**transcribe_podcasts_config)

    # Stage 3: Diarize podcasts
    logger("\n" + "=" * 60)
    logger("STAGE 3: Diarizing podcasts")
    logger("=" * 60)
    diarize_podcasts(**diarize_podcasts_config)

    logger("\n" + "=" * 60)
    logger("ETL PIPELINE COMPLETE")
    logger("=" * 60)

if __name__ == '__main__':
    etl(RSS_FEED)

