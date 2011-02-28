# Introduction

This is a reference application for tracking goals and soliciting donations to provide
incentive to complete your goals. The donations are sent to 3rd parties and not to the
owner of the goal application and payments are handled through PayPal's Adaptive
Payments APIs. In particular, we're using Parallel Payments to split a donation amount
between multiple charities defined by the goal application.

# Prerequisites

* Google App Engine SDK for Python downloaded and installed. You can find this at:
  http://code.google.com/appengine/downloads.html

* A working knowledge of the Google App Engine and Django projects. We're NOT using
  the app engine supplied Django framework, but instead we're using a great project
  that has modified the latest Django to be used with app engine. For information
  on these great projects see the following links:
    http://code.google.com/appengine/docs/python/gettingstarted/
    http://www.djangoproject.com/
    http://www.allbuttonspressed.com/projects/django-nonrel

* A modern web browser (Safari, Chrome, Firefox) because the client-side charting 
  framework is implemented using Protovis -- a powerful JavaScript and SVG-based 
  framework for web-native visualizations: http://vis.stanford.edu/protovis/

# Project Structure

Below is a quick overview of the individual components of the GAE project.

* app.yaml - Configuration file for app engine. The main thing you'll need to change
  in this file is the application parameter that defines the name of your application
  on app engine. See http://appengine.google.com for creating an application.

* urls.py - The mapping of allowed URL endpoints to the code that handles them.

* donate - Directory containing view logic and model definitions for the project.

* templates - Directory containing all template files for the project

* static - Directory containing static files (images, stylesheets, etc) for the 
project

* settings.py - The settings module for Django projects. It also contains project- 
specific properties for PayPal and Charity definitions. You'll need to modify
several of the PayPal properties in this file to use your own PayPal account. Pay
special attention to the "CHARITIES" list in settings.py as it is where you'll
define the charities available to goal applications.

# Screenshot

![screenshot!](https://github.com/zaffra/Donate/raw/master/screenshot.png)

Provided by: Zaffra, LLC - http://zaffra.com
