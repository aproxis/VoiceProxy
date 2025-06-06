import argparse
import logging
import os
from pathlib import Path
import csv

from .config import TTSConfig
from .proxy_manager import ProxyRotator
from .processor import TTSProcessor

logger = logging.getLogger(__name__)

def test_proxy_connection(proxy_rotator: ProxyRotator):
    """Test proxy connection"""
    if not proxy_rotator.proxies:
        logger.info("No proxy configuration found, using direct connection")
        return True
        
    logger.info("Testing proxy connections...")
    proxy_rotator.test_all_proxies()
    
    stats = proxy_rotator.get_proxy_stats()
    working_proxies = stats['total_proxies'] - stats['failed_proxies']
    
    if working_proxies > 0:
        logger.info(f"Proxy test complete: {working_proxies}/{stats['total_proxies']} proxies working")
        return True
    else:
        logger.error("No working proxies found")
        return False

def create_sample_proxy_config():
    """Create sample proxy configuration file"""
    sample_content = """ip,port,login,password,type
proxy1.example.com,8080,username1,password1,http
proxy2.example.com,8080,username2,password2,https
"""
    
    proxy_file = Path("proxies.csv")
    if not proxy_file.exists():
        with open(proxy_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        logger.info(f"Sample proxy configuration created: {proxy_file}")

def create_sample_api_config():
    """Create sample API key configuration file"""
    sample_content = """API,Date,available_tokens,last_checked
your_api_key_1,01.01.2024,100000,2024-01-01T00:00:00
your_api_key_2,01.01.2024,100000,2024-01-01T00:00:00
your_api_key_3,01.01.2024,100000,2024-01-01T00:00:00
"""
    
    api_file = Path("BASE.csv")
    if not api_file.exists():
        with open(api_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        logger.info(f"Sample API configuration created: {api_file}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Text-to-Speech conversion script')
    parser.add_argument(
        '--lang', type=str, default='RU',
        help='Language code for Excel sheet selection (default: RU)'
    )
    parser.add_argument(
        '--config', type=str, help='Path to configuration file'
    )
    parser.add_argument(
        '--create-samples', action='store_true',
        help='Create sample configuration files'
    )
    parser.add_argument(
        '--test-proxies', action='store_true',
        help='Test proxy connections only'
    )
    parser.add_argument(
        '--test-api-switching', action='store_true',
        help='Enable test mode for API switching (artificially reduces tokens)'
    )
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    # Create sample configurations if requested
    if args.create_samples:
        create_sample_proxy_config()
        create_sample_api_config()
        logger.info("Sample configuration files created. Please edit them with your actual values.")
        return
    
    # Initialize configuration
    config = TTSConfig()
    
    # Set test_api_switching_mode based on argument
    if args.test_api_switching:
        config.test_api_switching_mode = True
        logger.info("API switching test mode enabled.")

    # Initialize proxy rotator
    proxy_rotator = ProxyRotator(config.proxies_file)
    
    # Test proxies if requested
    if args.test_proxies:
        test_proxy_connection(proxy_rotator)
        return
    
    # Test proxy connection on startup
    if config.proxy_test_on_startup:
        if not test_proxy_connection(proxy_rotator):
            logger.warning("Continuing without working proxies...")
    
    # Initialize processor and start processing
    processor = TTSProcessor(config)
    language = args.lang.upper()
    processor.process_texts(language)

if __name__ == "__main__":
    main()
