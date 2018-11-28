""" Django management command to find unfulfilled baskets. """

import logging
from datetime import datetime

import pytz
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Subquery
from oscar.core.loading import get_model

logger = logging.getLogger(__name__)
Basket = get_model('basket', 'Basket')
PaymentProcessorResponse = get_model('payment', 'PaymentProcessorResponse')


class IncorrectRange(Exception):
    """
    Exception raised explicitly when end date is prior to start date
    """
    pass


class Command(BaseCommand):
    help = """
    Management command to find unfulfilled baskets.

    This management command is responsible for checking the baskets
    and finding out the baskets for which the payment form was submitted.

    Date format: yyyy-mm-dd
    Start date should be prior to End date

    Example:
        $ ... find_unfulfilled_baskets -s 2018-11-01 -e 2018-11-02
    """

    def add_arguments(self, parser):
        parser.add_argument('-s', '--start-date',
                            dest='start_date',
                            required=True,
                            help='start date (yyyy-mm-dd)')
        parser.add_argument('-e', '--end-date',
                            dest='end_date',
                            required=True,
                            help='end date (yyyy-mm-dd)')

    def handle(self, *args, **options):
        """
        Handler for the command

        It checks for date format and range validity and then
        calls find_unfulfilled_baskets for the given date range
        """
        try:
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d')
            if end_date < start_date:
                raise IncorrectRange('Incorrect date range')
        except (ValueError, IncorrectRange):
            logger.exception('Incorrect date format or Range')
            raise

        start_date = pytz.utc.localize(start_date)
        end_date = pytz.utc.localize(end_date)

        self.find_unfulfilled_baskets(start_date, end_date)

    def find_unfulfilled_baskets(self, start_date, end_date):
        """ Find baskets that are Frozen and unfulfilled """
        frozen_baskets = Basket.objects.filter(status='Frozen', date_submitted=None)
        frozen_baskets = frozen_baskets.filter(Q(date_created__range=(start_date, end_date)) |
                                               Q(date_merged__range=(start_date, end_date)))
        unfulfilled_baskets = frozen_baskets.exclude(id__in=Subquery(
            PaymentProcessorResponse.objects.values_list('basket_id')))

        if not unfulfilled_baskets:
            logger.info("No unfulfilled baskets found")
        else:
            basket_ids = "Basket ids : "
            for unfulfilled_basket in unfulfilled_baskets:
                basket_ids += str(unfulfilled_basket.id) + " ,"
            logger.info("Unfulfilled baskets found : " + basket_ids)
            raise CommandError(basket_ids)
