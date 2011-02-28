from django.db import models
from djangotoolbox.fields import ListField
from django.contrib.auth.models import User

class CommonModel(models.Model):
    """
    CommonModel contains the common fields most all other
    models will use.
    """
    # Auto datetime when created
    created_datetime = models.DateTimeField(auto_now_add=True)

    # Auto updated when models are saved 
    updated_datetime = models.DateTimeField(auto_now=True)

    # Is this model active and usable?
    is_active = models.BooleanField(default=True)

    class Meta:
        # makes this model abstract such that it cannot
        # be instantiated into an actual table and only
        # useful for model inheritance
        abstract = True


class Charity(CommonModel):
    """
    A model for storing a Charity.
    """

    # charity name
    name = models.CharField(max_length=32)

    # charity email address
    email = models.EmailField()

class Application(CommonModel):
    """
    A model for storing a user's Application
    """

    # the owner of the application
    user = models.ForeignKey(User)

    # readable name of the application
    name = models.CharField(max_length=32, unique=True)

    # unique identifier of the application for URL mapping
    slug = models.SlugField(max_length=32, unique=True)

    # description of the application
    description = models.TextField()

    # goal value 
    goal_value = models.IntegerField()

    # unit of the goal value (singular and plural could be
    # combined, but I'm taking the easy route and asking
    # the user)
    goal_units_singular = models.CharField(max_length=32)
    goal_units_plural = models.CharField(max_length=32)

    # the list of charities supported by the application
    charities = ListField()


class Donation(CommonModel):
    """
    A model for the donations being made for a particular 
    application. It tracks the associated application, the
    donation amount, and the PayPal payKey for the donation.

    Note: Until a donation is complete and successful, the is_active 
    field will be set to False
    """

    # The PayPal payKey associated with this donation. We use
    # the payKey to lookup the appropriate donation during all
    # PayPal transaction flows. 
    pay_key = models.CharField(max_length=32)

    # The application owning this donation
    application = models.ForeignKey(Application)

    # The amount of the donation. Handles up to 999.99
    amount = models.DecimalField(max_digits=5, decimal_places=2)


class ProgressUpdate(CommonModel):
    """
    Used to track the updates to a user's goal. Each instance 
    will have a date and value associated.
    """
    # The application owning this update
    application = models.ForeignKey(Application)

    # the value of this update set by the owner
    value = models.FloatField()
