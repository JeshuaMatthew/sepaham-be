# src/app/Core/logger.py
import logging

def setup_logger():
    logger = logging.getLogger("uvicorn.error")
  
    
    return logger

app_logger = setup_logger()
