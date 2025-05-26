# notification_factory.py
"""
Module for factory class that creates notification strategy objects.

This module provides a factory pattern implementation for creating
notification strategy instances. It maintains a registry of available
strategies and creates instances based on notification type requests.
"""
from typing import Dict, Type, Optional
import logging

# Import notification strategies
from notification_strategy import (
    NotificationStrategy, 
    ModelReviewNotification,
    PerformanceDegradationNotification, 
    EthicsAssessmentNotification
)

logger = logging.getLogger(__name__)

class NotificationFactory:
    """
    Factory class for creating notification strategy objects.
    
    This factory maintains a registry of notification strategy classes
    and creates instances on demand. It supports both built-in strategies
    and custom strategies that can be registered at runtime.
    """
    
    # Class variable to store strategy classes
    _strategies: Dict[str, Type[NotificationStrategy]] = {}
    
    @classmethod
    def register_strategy(cls, notification_type: str, strategy_class: Type[NotificationStrategy]) -> None:
        """
        Register a notification strategy class for a given type.
        
        Args:
            notification_type: Type identifier for the notification (e.g., "model_review").
            strategy_class: Class that implements NotificationStrategy interface.
            
        Raises:
            TypeError: If strategy_class doesn't implement NotificationStrategy.
        """
        # Validate that the strategy class implements the interface
        if not issubclass(strategy_class, NotificationStrategy):
            raise TypeError(f"Strategy class {strategy_class.__name__} must implement NotificationStrategy interface")
        
        cls._strategies[notification_type] = strategy_class
        logger.info(f"Registered strategy class {strategy_class.__name__} for type '{notification_type}'")
    
    @classmethod
    def create_notification(cls, notification_type: str) -> Optional[NotificationStrategy]:
        """
        Factory method to create the appropriate notification strategy.
        
        Args:
            notification_type: Type of notification to create (e.g., "model_review").
            
        Returns:
            Instance of the appropriate NotificationStrategy subclass,
            or None if the notification type is not registered.
        """
        strategy_class = cls._strategies.get(notification_type)
        
        if strategy_class:
            try:
                instance = strategy_class()
                logger.debug(f"Created {strategy_class.__name__} instance for type '{notification_type}'")
                return instance
            except Exception as e:
                logger.error(f"Failed to create strategy instance for type '{notification_type}': {e}")
                return None
        else:
            logger.warning(f"No strategy registered for notification type: '{notification_type}'")
            return None
    
    @classmethod
    def get_registered_types(cls) -> list[str]:
        """
        Get a list of all registered notification types.
        
        Returns:
            List of registered notification type identifiers.
        """
        return list(cls._strategies.keys())
    
    @classmethod
    def is_registered(cls, notification_type: str) -> bool:
        """
        Check if a notification type is registered.
        
        Args:
            notification_type: Type identifier to check.
            
        Returns:
            True if the type is registered, False otherwise.
        """
        return notification_type in cls._strategies
    
    @classmethod
    def unregister_strategy(cls, notification_type: str) -> bool:
        """
        Unregister a notification strategy.
        
        Args:
            notification_type: Type identifier to unregister.
            
        Returns:
            True if strategy was unregistered, False if it wasn't registered.
        """
        if notification_type in cls._strategies:
            del cls._strategies[notification_type]
            logger.info(f"Unregistered strategy for type '{notification_type}'")
            return True
        else:
            logger.warning(f"Cannot unregister - no strategy found for type '{notification_type}'")
            return False

def initialize_default_strategies() -> None:
    """
    Initialize the factory with built-in notification strategies.
    
    This function registers all the default strategies that come with
    the system. It's called automatically when the module is imported.
    """
    try:
        NotificationFactory.register_strategy("model_review", ModelReviewNotification)
        NotificationFactory.register_strategy("performance_degradation", PerformanceDegradationNotification)
        NotificationFactory.register_strategy("ethics_assessment", EthicsAssessmentNotification)
        
        logger.info("Initialized NotificationFactory with default strategies")
        
    except Exception as e:
        logger.error(f"Failed to initialize default notification strategies: {e}")

# Automatically initialize default strategies when module is imported
initialize_default_strategies()