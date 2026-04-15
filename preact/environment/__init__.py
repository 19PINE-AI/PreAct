"""Computer Environment Interface — abstraction for browser/VM interaction."""

from preact.environment.base import ComputerEnvironment
from preact.environment.browser import BrowserEnvironment

__all__ = ["ComputerEnvironment", "BrowserEnvironment"]
