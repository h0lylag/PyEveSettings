"""Window settings management for PyEveSettings."""

from typing import Optional, Tuple


class WindowSettings:
    """Manages window geometry and positioning."""
    
    def __init__(self, width: int = 800, height: int = 600, 
                 x_pos: int = 0, y_pos: int = 0):
        """Initialize window settings.
        
        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            x_pos: X position on screen.
            y_pos: Y position on screen.
        """
        self.width = width
        self.height = height
        self.x_pos = x_pos
        self.y_pos = y_pos
    
    def get_geometry_string(self) -> str:
        """Get tkinter geometry string.
        
        Returns:
            String in format: "{width}x{height}+{x}+{y}"
        """
        return f"{self.width}x{self.height}+{self.x_pos}+{self.y_pos}"
    
    def should_center(self) -> bool:
        """Check if window should be centered (no saved position).
        
        Returns:
            True if both x_pos and y_pos are 0, False otherwise.
        """
        return self.x_pos == 0 and self.y_pos == 0
    
    def update(self, width: int, height: int, x_pos: int, y_pos: int) -> None:
        """Update all window settings.
        
        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            x_pos: X position on screen.
            y_pos: Y position on screen.
        """
        self.width = width
        self.height = height
        self.x_pos = x_pos
        self.y_pos = y_pos
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary with width, height, x_pos, y_pos keys.
        """
        return {
            'width': self.width,
            'height': self.height,
            'x_pos': self.x_pos,
            'y_pos': self.y_pos
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WindowSettings':
        """Create WindowSettings from dictionary.
        
        Args:
            data: Dictionary with width, height, x_pos, y_pos keys.
            
        Returns:
            WindowSettings instance.
        """
        return cls(
            width=data.get('width', 800),
            height=data.get('height', 600),
            x_pos=data.get('x_pos', 0),
            y_pos=data.get('y_pos', 0)
        )
