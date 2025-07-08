# notification_factory.py
"""
Module for factory class that creates notification strategy objects.

This module provides a factory pattern implementation for creating
notification strategy instances. It maintains a registry of available
strategies and creates instances based on notification type requests.
"""
from __future__ import annotations
from typing import Dict, Type, Optional, List, TYPE_CHECKING
from enum import Enum
from loguru import logger

if TYPE_CHECKING:
    from notification_strategy import NotificationStrategy


class NotificationType(Enum):
    """Enum for standard notification types to prevent typos and improve type safety."""
    MODEL_REVIEW = "model_review"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ETHICS_ASSESSMENT = "ethics_assessment"


class NotificationFactory:
    """
    Factory class for creating notification strategy objects.
    
    This factory maintains a registry of notification strategy classes
    and creates instances on demand. It supports both built-in strategies
    and custom strategies that can be registered at runtime.
    """
    
    # Class variable to store strategy classes
    _strategies: Dict[str, Type[NotificationStrategy]] = {}
    _initialized = False
    
    @classmethod
    def register_strategy(cls, notification_type: str, strategy_class: Type[NotificationStrategy], 
                         allow_override: bool = False) -> None:
        """
        Register a notification strategy class for a given type.
        
        Args:
            notification_type: Type identifier for the notification (e.g., "model_review").
            strategy_class: Class that implements NotificationStrategy interface.
            allow_override: Whether to allow overriding existing registrations.
            
        Raises:
            TypeError: If strategy_class doesn't implement NotificationStrategy.
            ValueError: If notification_type is already registered and allow_override is False.
        """
        if not notification_type or not isinstance(notification_type, str):
            raise ValueError("notification_type must be a non-empty string")
        
        if not strategy_class:
            raise ValueError("strategy_class cannot be None")
        
        # Import here to avoid circular imports
        from notification_strategy import NotificationStrategy
        
        # Validate that the strategy class implements the interface
        if not issubclass(strategy_class, NotificationStrategy):
            raise TypeError(f"Strategy class {strategy_class.__name__} must implement NotificationStrategy interface")
        
        # Validate that the strategy class can be instantiated
        try:
            test_instance = strategy_class()
            # Check for required methods (assuming NotificationStrategy has a send_notification method)
            if not hasattr(test_instance, 'send_notification'):
                raise TypeError("Strategy must implement send_notification method")
        except Exception as e:
            raise TypeError(f"Cannot instantiate strategy class {strategy_class.__name__}: {e}")
        
        # Check if we're trying to override a default strategy without permission
        default_types = {nt.value for nt in NotificationType}
        if notification_type in default_types and not allow_override:
            if notification_type in cls._strategies:
                existing_class = cls._strategies[notification_type]
                raise ValueError(f"Cannot override default strategy '{notification_type}' "
                               f"({existing_class.__name__}). Use allow_override=True to replace.")
        
        # Check for existing registration
        action = "Overrode" if notification_type in cls._strategies else "Registered"
        
        if notification_type in cls._strategies and not allow_override:
            existing_class = cls._strategies[notification_type]
            raise ValueError(f"Strategy for type '{notification_type}' already registered "
                           f"({existing_class.__name__}). Use allow_override=True to replace.")
        
        cls._strategies[notification_type] = strategy_class
        logger.info(f"{action} strategy class {strategy_class.__name__} for type '{notification_type}'")
    
    @classmethod
    def create_notification(cls, notification_type: str) -> Optional[NotificationStrategy]:
        """
        Factory method to create the appropriate notification strategy.
        
        Args:
            notification_type: Type of notification to create (e.g., "model_review").
            
        Returns:
            Instance of the appropriate NotificationStrategy subclass,
            or None if the notification type is not registered.
            
        Raises:
            ValueError: If notification_type is empty or None.
        """
        if not notification_type or not isinstance(notification_type, str):
            raise ValueError("notification_type must be a non-empty string")
        
        # Ensure default strategies are initialized
        cls._ensure_initialized()
        
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
            logger.warning(f"No strategy registered for notification type: '{notification_type}'. "
                          f"Available types: {cls.get_registered_types()}")
            return None
    
    @classmethod
    def get_registered_types(cls) -> List[str]:
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
        if not notification_type or not isinstance(notification_type, str):
            return False
        
        return notification_type in cls._strategies
    
    @classmethod
    def unregister_strategy(cls, notification_type: str) -> bool:
        """
        Unregister a notification strategy.
        
        Args:
            notification_type: Type identifier to unregister.
            
        Returns:
            True if strategy was unregistered, False if it wasn't registered.
            
        Raises:
            ValueError: If attempting to unregister a default strategy.
        """
        if not notification_type or not isinstance(notification_type, str):
            return False
        
        # Protect default strategies from unregistration
        default_types = {nt.value for nt in NotificationType}
        if notification_type in default_types:
            logger.warning(f"Cannot unregister default strategy '{notification_type}'. "
                          f"Use allow_override=True in register_strategy() to replace it.")
            return False
        
        if notification_type in cls._strategies:
            del cls._strategies[notification_type]
            logger.info(f"Unregistered strategy for type '{notification_type}'")
            return True
        else:
            logger.warning(f"Cannot unregister - no strategy found for type '{notification_type}'")
            return False
    
    @classmethod
    def clear_all_strategies(cls) -> None:
        """
        Clear all registered strategies. Use with caution.
        
        This method is primarily intended for testing purposes.
        """
        cls._strategies.clear()
        cls._initialized = False
        logger.warning("Cleared all registered notification strategies")
    
    @classmethod
    def get_strategy_info(cls) -> Dict[str, str]:
        """
        Get information about all registered strategies.
        
        Returns:
            Dictionary mapping notification types to strategy class names.
        """
        return {notification_type: strategy_class.__name__ 
               for notification_type, strategy_class in cls._strategies.items()}
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """
        Ensure default strategies are initialized (lazy initialization).
        """
        if not cls._initialized:
            cls._initialize_default_strategies()
            cls._initialized = True
    
    @classmethod
    def _initialize_default_strategies(cls) -> None:
        """
        Initialize the factory with built-in notification strategies.
        
        This function registers all the default strategies that come with
        the system. Uses lazy imports to avoid circular dependencies.
        """
        try:
            # Import strategies here to avoid circular imports
            from notification_strategy import (
                ModelReviewNotification,
                PerformanceDegradationNotification, 
                EthicsAssessmentNotification
            )
            
            # Register default strategies using enum values
            cls._strategies[NotificationType.MODEL_REVIEW.value] = ModelReviewNotification
            cls._strategies[NotificationType.PERFORMANCE_DEGRADATION.value] = PerformanceDegradationNotification
            cls._strategies[NotificationType.ETHICS_ASSESSMENT.value] = EthicsAssessmentNotification
            
            logger.info("Initialized NotificationFactory with default strategies: "
                       f"{list(cls._strategies.keys())}")
            
        except ImportError as e:
            logger.error(f"Failed to import notification strategies: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize default notification strategies: {e}")
            raise


def get_factory() -> Type[NotificationFactory]:
    """
    Get the notification factory instance.
    
    This function provides a convenient way to access the factory
    and ensures it's properly initialized.
    
    Returns:
        NotificationFactory class (singleton-like behavior).
    """
    NotificationFactory._ensure_initialized()
    return NotificationFactory


# Convenience functions for common operations
def create_notification(notification_type: str) -> Optional[NotificationStrategy]:
    """
    Convenience function to create a notification strategy.
    
    Args:
        notification_type: Type of notification to create.
        
    Returns:
        Instance of the appropriate NotificationStrategy subclass,
        or None if the notification type is not registered.
    """
    return get_factory().create_notification(notification_type)


def register_custom_strategy(notification_type: str, strategy_class: Type[NotificationStrategy]) -> None:
    """
    Convenience function to register a custom notification strategy.
    
    Args:
        notification_type: Type identifier for the notification.
        strategy_class: Class that implements NotificationStrategy interface.
    """
    get_factory().register_strategy(notification_type, strategy_class)