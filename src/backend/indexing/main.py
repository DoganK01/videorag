import asyncio
import argparse
import logging
import logging.config
import os
import yaml
from dotenv import load_dotenv

from app.core.resources import initialize_resources, close_all_resources
from app.indexing.pipeline import IndexingPipeline


try:
    with open("configs/logging_config.yaml", "rt") as f:
        log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)
except FileNotFoundError:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
    )
    logging.warning("logging_config.yaml not found. Using basic logging configuration.")

logger = logging.getLogger(__name__)

async def run_indexing_for_path(path: str):
    """
    The main, reusable entry point for the entire indexing process.
    It initializes all resources via the central manager and runs the pipeline.
    This function can now be easily tested or called from other modules if needed.
    """
    logger.info(f"Starting full indexing process for path: {path}")
    resources = None
    try:
        logger.info("Loading application configuration...")
        with open("configs/main_config.yaml", "rt") as f:
            config = yaml.safe_load(f.read())
        
        resources = await initialize_resources(config)
        
        pipeline = IndexingPipeline(
            job_id=None, # No job_id for direct command-line runs
            config=config,
            models=resources['models'],
            stores=resources['stores']
        )
        if os.path.isdir(path):
            video_files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
        elif os.path.isfile(path):
            video_files = [path]
        else:
            raise FileNotFoundError(f"Provided path is not a valid file or directory: {path}")

        if not video_files:
            logger.warning(f"No video files found at path: {path}")
            return

        logger.info(f"Found {len(video_files)} video(s) to process.")
        
        for video_file in video_files:
            await pipeline.run_for_video(video_file)

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
    except Exception as e:
        logger.critical(f"A critical error occurred during the indexing process for path {path}.", exc_info=True)
    finally:
        if resources and resources.get('stores'):
            await close_all_resources(resources['stores'])

def main_cli():
    """
    The clean entry point function for running this script from the command line.
    Its only job is to handle command-line arguments and start the async event loop.
    """
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Run the VideoRAG offline indexing pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--video-path",
        type=str,
        required=True,
        help="Path to a single video file or a directory containing video files to be indexed."
    )
    args = parser.parse_args()
    
    asyncio.run(run_indexing_for_path(args.video_path))

if __name__ == "__main__":
    main_cli()