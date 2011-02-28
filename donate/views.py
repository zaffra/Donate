from donate.models import *
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import Context, RequestContext, Template
from django.contrib import messages, auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from random import randrange

import settings
import paypal
import re
import simplejson

import logging
logging.basicConfig(level=logging.DEBUG)

##
# Constants
##

TEMPLATE_INDEX = "index.html"
TEMPLATE_REGISTER = "register.html"
TEMPLATE_ACCOUNT = "account.html"
TEMPLATE_CREATE_EDIT_APPLICATION = "create_edit_application.html"
TEMPLATE_VIEW_APPLICATION = "view_application.html"
TEMPLATE_CONFIRM_DONATION = "confirm_donation.html"


VALID_APPLICATION_NAME_PATTERN = re.compile("^[a-zA-Z0-9 ]*$")

##
# Utility methods
##

def render(request, view, context={}):
    """
    Renders a template with a RequestContext. RequestContext will
    allow your templates access to the request object. For info see:
    http://bit.ly/gGyzqX
    """
    if (request):
        return render_to_response(view, 
                                  context, 
                                  context_instance=RequestContext(request))

    return render_to_response(view, context)

def render_pprint(object):
    """
    Quick and dirty way of dumping a JSON-serializable object
    to the view for inspection
    """
    s = simplejson.dumps(object, indent=4)
    return HttpResponse(s, mimetype="text/plain")

def create_random_datetime(start, end):
    """
    This function will return a random datetime between two datetime 
    objects.

    Borrowed from: http://bit.ly/gM45o4
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return (start + timedelta(seconds=random_second))


##
# View methods
##

def index(request):
    """
    The view shown when a user is not authenticated
    """
    if request.user.is_authenticated():
        return redirect(account)
    return render(request, TEMPLATE_INDEX)

def register(request):
    """
    View to handle registering for an account. GET requests simply
    render the template and POST requests are for creating the 
    account.
    """
    if request.method == "GET":
        return render(request, TEMPLATE_REGISTER)

    # Registration parameters
    first_name = request.POST.get("first_name", "")
    last_name = request.POST.get("last_name", "")
    email = request.POST.get("email", "")
    password = request.POST.get("password", "")
    password2 = request.POST.get("password2", "")

    # Validate the required fields
    error = False
    if not first_name:
        error = True
        messages.error(request, "First name is required.")

    if not last_name:
        error = True
        messages.error(request, "Last name is required.")

    if not email:
        error = True
        messages.error(request, "Email address is required.")

    if not password or not password2:
        error = True
        messages.error(request, "Both password fields are required.")
    elif password != password2:
        error = True
        messages.error(request, "Passwords must equal.")

    if not error:
        # check for existing user
        try:
            User.objects.get(username=email)
            error = True
        except User.DoesNotExist:
            # No existing user with that email...this is good
            pass

    # Render the template with errors if needed
    if error:
        return render(request, TEMPLATE_REGISTER, {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        })

    # create a new user object
    user = User.objects.create_user(username=email, 
                                    email=email, 
                                    password=password)
    user.first_name = first_name
    user.last_name = last_name
    user.save()
    
    # Redirect to the home page so they can login
    messages.success(request, "Registration successful. Please sign in.")
    return redirect(index)

@login_required
def account(request):
    """
    Render the account page template
    """
    return render(request, TEMPLATE_ACCOUNT)

@login_required
def update_progress(request):
    """
    Logic to create a new progress model for the given application id
    """
    # validate a POST request
    if request.method != "POST":
        return redirect(index)

    # validate the app id was given
    app_id = request.POST.get("app_id", "")
    if not app_id:
        return redirect(index)

    # validate that the application exists and the user is the owner
    try:
        app = Application.objects.get(pk=int(app_id), user=request.user)
    except Application.DoesNotExist:
        messages.error(request, "Application with id %s does not exist." % app_id)
        return redirect(index)

    # validate progress exists
    progress = request.POST.get("progress", "")
    if not progress:
        messages.error(request, "Progress is required.")
        return redirect(view_application, slug=app.slug)

    # validate the progress
    try:
        float(progress)
    except ValueError:
        messages.error(request, "Progress must be a number.")
        return redirect(view_application, slug=app.slug)

    # Create the progress udpate and save it
    pu = ProgressUpdate(application=app, value=progress)
    pu.save()

    # return back to the application with a thank you message
    messages.success(request, "Progress udpated.")
    return redirect(view_application, slug=app.slug)

def donate(request):
    """
    View to confirm the user wants to start the donation transaction. Here
    we validate a few things and then execute a PayPal Pay request to obtain
    a valid payKey. The payKey will be used in the template for the "Donate"
    button that will redirect them to PayPal to complate the transaction.
    """

    # validate a POST request
    if request.method != "POST":
        return redirect(index)

    # validate the app id was given
    app_id = request.POST.get("app_id", "")
    if not app_id:
        return redirect(index)

    # validate that the application exists
    try:
        app = Application.objects.get(pk=int(app_id))
    except Application.DoesNotExist:
        messages.error(request, "Application with id %s does not exist." % app_id)
        return redirect(index)

    # validate the donation exists
    donation_amount = request.POST.get("donation", "")
    if not donation_amount:
        messages.error(request, "Donation is required.")
        return redirect(view_application, slug=app.slug)

    # validate the amount
    try:
        float(donation_amount)
    except ValueError:
        messages.error(request, "Donation must be a number.")
        return redirect(view_application, slug=app.slug)

    # get the list of charities supporting this application
    supporting_charities = Charity.objects.filter(pk__in=app.charities)

    # begin the payment process by sending a Pay API request to
    # PayPal to obtain a payKey that will be used when redirecting
    # to PayPal for completing the transaction
    response = paypal.create_pay_request(float(donation_amount), supporting_charities)
    
    errors = paypal.get_errors(response)
    if errors:
        [logging.error(e) for e in errors]

    # Execute the Pay request
    pay_key = paypal.get_pay_key(response)

    # if we have a valid payKey we can create an inactive Donation object using
    # the payKey as a lookup field for after the transaction has been complete
    # and PayPal has redirected back to our site
    if pay_key:
        d = Donation(pay_key=pay_key, 
                     application=app, 
                     amount=donation_amount,
                     is_active=False)
        d.save()

    # Render the template with the required context information
    return render(request, TEMPLATE_CONFIRM_DONATION, {
        "pay_key": pay_key,
        "application": app,
        "donation_amount": donation_amount,
        "supporting_charities": supporting_charities
    })

def cancel_donation(request):
    """
    User canceled the donation transaction on PayPal. We could delete
    the donation object, but instead we'll keep it around so we can do
    analysis at a later time to see how many people actually click
    the Donate button, but decided to not complete it.

    We will lookup the application based on the payKey in the query
    string and redirect back to that app.
    """
    messages.info(request, "Your donation has been canceled!")

    try:
        # get the payKey and redirect to the associated application
        pay_key = request.GET.get("payKey")
        donation = Donation.objects.get(pay_key=pay_key)
        return redirect(view_application, slug=donation.application.slug)
    except Donation.DoesNotExist:
        # Do nothing. Maybe log it.
        pass

    return redirect(index)

def finish_donation(request):
    """
    A donation was successfull. Look up the donation object via the payKey
    query string parameter and set the donation object to be active. Then
    we redirect back to the application.
    """

    messages.success(request, "Your donation was successful! Thank you very much!")

    try:
        # get the payKey from the query string
        pay_key = request.GET.get("payKey")

        # look up the donation that matches that payKey and update the created
        # datetime as well as the is_active field
        donation = Donation.objects.get(pay_key=pay_key)
        donation.is_active = True
        donation.created_datetime = datetime.utcnow()
        donation.save()
        return redirect(view_application, slug=donation.application.slug)
    except Donation.DoesNotExist:
        # Do nothing. Maybe log it.
        pass

    return redirect(index)

def view_application(request, slug=None):
    """
    View method to view the application matching the given slug.
    """

    # grab the application or throw a 404
    app = get_object_or_404(Application, slug=slug)

    # now
    now = datetime.utcnow()

    # get the donations
    donations = app.donation_set.filter(is_active=True).order_by('-created_datetime')

    # sum of the donations
    total_donations = sum([d.amount for d in donations])

    # application start time and today's date. Used to iterate over the days to
    # group donations and updates to the application for charting
    start_date = app.created_datetime
    end_date = datetime.utcnow()

    # Build up a data structure that will bin date strings to the donation
    # amount for that date. The x-value will be the zero-based day index and
    # the y-value is the total donations for that date
    bins = {}
    for n in range((end_date-start_date).days+1):
        date = start_date + timedelta(days=n)
        date_string = "%d/%d/%d" % (date.month, date.day, date.year)
        bins[date_string] = {"x": n, "date_string": date_string, "y": 0}

    for donation in donations:
        date_string = "%d/%d/%d" % (
            donation.created_datetime.month,
            donation.created_datetime.day,
            donation.created_datetime.year,
        )
        bins[date_string]["y"] += float(donation.amount)

    # we have them in day bins, now put them into a json list sorted by date
    sorted_keys = sorted(bins.keys())
    goal_donations = simplejson.dumps([bins[k] for k in sorted_keys])

    # now we're essentially going to do the same thing for updates. The major
    # difference is that we aren't taking a sum of the updates for a given day, but
    # rather we'll take the last value for a given day. That way the user can provide
    # as many updates as they want during the day, but ultimately the last one on any
    # given day gets used

    # get the updates for this application
    updates = app.progressupdate_set.all().order_by('-created_datetime')

    # the currently used application update
    if updates:
        current_value = updates[0].value
    else:
        current_value = 0


    # Build up a data structure that will bin date strings to the last progress
    # update for that date.
    bins = {}
    for n in range((end_date-start_date).days+1):
        date = start_date + timedelta(days=n)
        date_string = "%d/%d/%d" % (date.month, date.day, date.year)
        bins[date_string] = {"x": n, "date_string": date_string, "y": 0}

    # for each update we store check to see if it's the latest update for
    # the given date_string bucket and if so we'll use that update
    for update in updates:
        date_string = "%d/%d/%d" % (
            update.created_datetime.month,
            update.created_datetime.day,
            update.created_datetime.year,
        )

        if "date" not in bins[date_string] or update.created_datetime > bins[date_string]["date"]:
            bins[date_string]["date"] = update.created_datetime
            bins[date_string]["y"] = update.value

    # remove the datetime object since we don't need it
    for d in bins.itervalues():
        if "date" in d:
            del d["date"]

    # we have them in day bins, now put them into a json list sorted on date
    sorted_keys = sorted(bins.keys())
    goal_updates = simplejson.dumps([bins[k] for k in sorted_keys])

    # get the list of charities supporting by this application
    supporting_charities = Charity.objects.filter(pk__in=app.charities)

    # render the template with the context
    return render(request, TEMPLATE_VIEW_APPLICATION, {
        "application": app,
        "supporting_charities": supporting_charities,
        "goal_updates": goal_updates,
        "goal_donations": goal_donations,
        "total_donations": total_donations,
        "current_value": current_value,
    })

@login_required
def create_edit_application(request, app_id=None):
    """
    Create a new application or edit an existing if app_id is given.
    """

    # begin building up a context to supply to the template
    base_context = {"charities": Charity.objects.all()}

    if request.method == "GET":
        # Edit an existing application by building up the context
        # with the details of the application
        if app_id is not None:
            try:
                app = Application.objects.get(pk=int(app_id))

                base_context.update({
                    "app_id": app.id,
                    "name": app.name,
                    "description": app.description,
                    "goal_value": app.goal_value,
                    "goal_units_singular": app.goal_units_singular,
                    "goal_units_plural": app.goal_units_plural,
                    "app_charities": app.charities,
                })

            except Application.DoesNotExist:
                messages.error(request, "Application with that ID does not exist.")

        return render(request, TEMPLATE_CREATE_EDIT_APPLICATION, base_context)

    # Being POST logic that will create or update and application
    app_id = request.POST.get("app_id", "")
    name = request.POST.get("name", "")
    description = request.POST.get("description", "")
    goal_value = request.POST.get("goal_value", "")
    goal_units_singular = request.POST.get("goal_units_singular", "")
    goal_units_plural = request.POST.get("goal_units_plural", "")
    charities = [int(i) for i in request.POST.getlist("charities")]

    error = False

    # check the app_id. if it exists we convert it to an integer and lookup the
    # application to make sure it exists
    app = None
    if app_id:
        try:
            app_id = int(app_id)
            app = Application.objects.get(pk=app_id)
        except Application.DoesNotExist:
            error = True
            messages.error(request, "Application with that ID does not exist.")
    else:
        # check duplicate application names
        try:
            Application.objects.get(name=name)
            error = True
            messages.error(request, "An application with that name already exists.")
        except Application.DoesNotExist:
            # this is ok
            pass

    # Required parameter "name"
    if not name:
        error = True
        messages.error(request, "Application name is required.")
    else:

        # check the name string
        m = re.match(VALID_APPLICATION_NAME_PATTERN, name)
        if m is None:
            error = True
            messages.error(request, "Application name may only contain letters, numbers, and underscores.")

    # Required parameter "description"
    if not description:
        error = True
        messages.error(request, "Application description is required.")

    # Required parameter "goal_value"
    if not goal_value:
        error = True
        messages.error(request, "Application goal value is required.")
    else:
        try:
            goal_value = int(goal_value)
            if goal_value <= 0:
                raise
        except:
            error = True
            messages.error(request, "Application goal value must be a number greater than one.")

    # Required parameter "goal_units_singular"
    if not goal_units_singular:
        error = True
        messages.error(request, "Application's singular goal units is required.")

    # Required parameter "goal_units_plural"
    if not goal_units_plural:
        error = True
        messages.error(request, "Application's plural goal units is required.")

    # Required parameter "charities"
    if not charities:
        error = True
        messages.error(request, "At least one charity is required.")

    # In the event of an error, we populate the context with their data
    # and render the template again with the error messages
    if error:
        base_context.update({
            "name": name,
            "description": description,
            "goal_value": goal_value,
            "goal_units_singular": goal_units_singular,
            "goal_units_plural": goal_units_plural,
            "app_charities": charities,
        })
        return render(request, TEMPLATE_CREATE_EDIT_APPLICATION, base_context)

    # the slug field is the lower case version of the name with
    # all spaces replaced with dashes. This makes for a readable
    # URL the user can link to
    slug = name.replace(" ", "-").lower()

    # if we're editing, update the application fields
    # we don't allow editing of app name or slug after it's
    # been created
    if app_id and app is not None:
        app.description = description
        app.goal_value = goal_value
        app.goal_units_singular = goal_units_singular
        app.goal_units_plural = goal_units_plural
        app.charities = charities
        messages.success(request, "Application updated!")

    # else we createa new application
    else: 
        app = Application(user=request.user,
                          name=name,
                          slug=slug,
                          description=description,
                          goal_value=goal_value,
                          goal_units_singular=goal_units_singular,
                          goal_units_plural=goal_units_plural,
                          charities=charities)

        messages.success(request, "Application created!")

    # Save the application and redirect to the account page
    app.save()

    return redirect(account)

@login_required
def delete_application(request, app_id=None):
    """
    Delete the application given the app id
    """
    if app_id is None:
        messages.error(request, "Application ID does not exist!")
    else:
        # get the application or raise 404
        app = get_object_or_404(Application, pk=int(app_id))

        # delete the application
        app.delete()
        messages.info(request, "Application deleted!")

    # redirect to the account page
    return redirect(account)

##
# Non view methods
##
def signin(request):
    """
    Handle user authentication
    """
    if request.method != "POST":
        messages.error(request, "Only POST requests are supported.")
        return redirect(index)

    # Required parameters
    email = request.POST.get("email", "")
    password = request.POST.get("password", "")

    # Try to authenticate
    user = auth.authenticate(username=email, password=password)

    # Log the user in and redirect to the account page
    if user is not None and user.is_active:
        messages.success(request, "You've successfully signed in.")
        auth.login(request, user)
        return redirect(account)
    
    # Bad credentials. Redirect with error message
    else:
        messages.error(request, "Unable to authenticate you. Please try again.")
        return redirect(index)

def signout(request):
    """
    Kill the user's session and redirect to the home page
    """
    auth.logout(request)
    return redirect(index)

def bootstrap(request):
    """
    A simple view that will bootstrap the database with values we
    need for development. In production you'll probably not want to
    expose something like this, but it's a nice thing to have on hand
    when you want to refresh the database to a good state.

    NOTE: this will clear the various database models before creating
    new ones.
    """

    # clear and create Charity objects
    Charity.objects.all().delete()
    for name, email in settings.CHARITIES:
        c = Charity(name=name, email=email)
        c.save()

    # clear and create users
    User.objects.all().delete()
    # Admin users
    u = User(first_name="John",
             last_name="Doe",
             email="john@example.com",
             username="john@example.com",
             is_staff=True,
             is_superuser=True,
             is_active=True)
    u.set_password("password")
    u.save()

    # clear and create applications
    Application.objects.all().delete()

    goal_value = 20
    a = Application(user=u,
                    name="Help John Lose Weight",
                    slug="help-john-lose-weight",
                    description="Please reward me for losing weight by contributing to my favorite charities.",
                    goal_value=goal_value,
                    goal_units_singular="pound",
                    goal_units_plural="pounds",
                    charities=[o['pk'] for o in Charity.objects.values('pk').all()])

    # now
    now = datetime.utcnow()

    # set the application to be one week ago
    a.created_datetime = now - timedelta(days=5)

    # save it
    a.save()

    # clear and create donations
    Donation.objects.all().delete()

    # Uncomment the following to create some random donations over the period 
    # of the application
    for i in range(25):
        random_datetime = create_random_datetime(a.created_datetime, now)
        d = Donation(application=a, amount=randrange(1, 12))
        d.created_datetime = random_datetime
        d.save()

    # clear and create some updates
    ProgressUpdate.objects.all().delete()

    # Uncomment the following to create some updates over the period 
    # of the application
    i = 1
    for n in range((now - a.created_datetime).days+1):
        dt = a.created_datetime + timedelta(days=n)
        u = ProgressUpdate(application=a, value=i)
        u.created_datetime = dt
        u.save()

        i += 2

    messages.success(request, "Database bootstrap complete...")
    return redirect(view_application, slug=a.slug)
