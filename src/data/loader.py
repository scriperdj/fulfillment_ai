"""
Data loading module for fulfillment_ai
Handles CSV loading and data validation
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Optional

from src.config import settings


logger = logging.getLogger(__name__)


class DataLoader:
    """Loads and manages order data"""

    def __init__(self, data_path: str = settings.data_path):
        self.data_path = Path(data_path)
        self.df: Optional[pd.DataFrame] = None

    def load_csv(self, filename: str) -> pd.DataFrame:
        """Load CSV file from data path"""
        filepath = self.data_path / filename
        logger.info(f"Loading data from {filepath}")

        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        try:
            self.df = pd.read_csv(filepath)
            logger.info(f"Loaded {len(self.df)} rows")
            return self.df
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise

    def get_data(self) -> pd.DataFrame:
        """Get currently loaded data"""
        if self.df is None:
            raise ValueError("No data loaded. Call load_csv() first.")
        return self.df

    def validate_data(self) -> bool:
        """Validate data schema"""
        if self.df is None:
            return False

        required_columns = {
            "Order Date", "Ship Date", "Segment", "Region", "Product Category"
        }
        return required_columns.issubset(set(self.df.columns))
