
from pathlib import Path

RSS_FEED = 'https://www.omnycontent.com/d/playlist/77bedd50-a734-42aa-9c08-ad86013ca0f9/3c014aab-9177-41d0-9705-ad8d012bc513/7cd8dba9-548c-479e-9bbe-ad8d012bc52f/podcast.rss'



DATA_DIR = Path('data')
DATA_DIR.mkdir(parents=True,exist_ok=True)

META_DIR = DATA_DIR / 'metadata'
META_DIR.mkdir(parents=True,exist_ok=True)

STG_1_DIR = DATA_DIR / 'stg_1_downloads'
STG_1_DIR.mkdir(parents=True,exist_ok=True)
STG_1_META = META_DIR / 'stg_1_downloads.json'

STG_2_DIR = DATA_DIR / 'stg_2_transcript'
STG_2_DIR.mkdir(parents=True,exist_ok=True)
STG_2_META = META_DIR / 'stg_2_transcript.json'