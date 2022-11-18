import datetime
from importlib.resources import _

from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError

from tapir.utils.forms import DateInput
from tapir.wirgarten.constants import DeliveryCycle, NO_DELIVERY
from tapir.wirgarten.models import (
    ProductType,
    Product,
    ProductCapacity,
    GrowingPeriod,
    TaxRate,
    PickupLocation,
    PickupLocationCapability,
)
from tapir.wirgarten.validators import (
    validate_date_range,
    validate_growing_period_overlap,
)

KW_PROD_ID = "prodId"
KW_PROD_TYPE_ID = "prodTypeId"
KW_PERIOD_ID = "periodId"


class ProductTypeForm(forms.Form):
    template_name = "wirgarten/product/product_type_form.html"

    def __init__(self, *args, **kwargs):
        super(ProductTypeForm, self).__init__(*args)
        initial_id = "-"
        initial_period_id = "-"
        initial_name = ""
        initial_delivery_cycle = NO_DELIVERY
        initial_capacity = None
        initial_tax_rate = 0
        product_type = None

        if KW_PROD_TYPE_ID in kwargs and KW_PERIOD_ID in kwargs:
            initial_id = kwargs[KW_PROD_TYPE_ID]
            initial_period_id = kwargs[KW_PERIOD_ID]
            product_type = ProductType.objects.get(id=initial_id)
            try:
                self.tax_rate = TaxRate.objects.get(
                    product_type=product_type, valid_to=None
                )
                initial_tax_rate = self.tax_rate.tax_rate
            except TaxRate.DoesNotExist:
                initial_tax_rate = 0.19  # FIXME: default value in tapir paramenter
            try:
                self.capacity = ProductCapacity.objects.get(
                    period__id=kwargs[KW_PERIOD_ID],
                    product_type__id=kwargs[KW_PROD_TYPE_ID],
                )
                initial_capacity = self.capacity.capacity
            except ProductCapacity.DoesNotExist:
                initial_capacity = 0

            initial_name = product_type.name
            initial_delivery_cycle = product_type.delivery_cycle

        self.fields["id"] = forms.CharField(
            initial=initial_id, widget=forms.HiddenInput()
        )
        self.fields["periodId"] = forms.CharField(
            initial=initial_period_id, widget=forms.HiddenInput()
        )
        self.fields["name"] = forms.CharField(
            initial=initial_name, required=True, label=_("Produkt Name")
        )
        self.fields["capacity"] = forms.FloatField(
            initial=initial_capacity, required=True, label=_("Produkt Kapazität (in €)")
        )
        self.fields["delivery_cycle"] = forms.ChoiceField(
            initial=initial_delivery_cycle,
            required=True,
            label=_("Liefer-/Abholzyklus"),
            choices=DeliveryCycle,
        )
        for location in PickupLocation.objects.all():
            initial_value = None
            if product_type is not None:
                initial_value = PickupLocationCapability.objects.filter(
                    pickup_location=location, product_type=product_type
                ).exists()
            self.fields["plc_" + location.id] = forms.BooleanField(
                label=location.name, required=False, initial=initial_value
            )
        self.fields["tax_rate"] = forms.FloatField(
            initial=initial_tax_rate,
            required=True,
            label=_("Mehrwertsteuersatz"),  # FIXME: format
        )


class ProductForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args)

        initial_id = "-"
        initial_type_id = "-"
        initial_name = ""
        initial_price = 0

        if KW_PROD_ID in kwargs:
            initial_id = kwargs[KW_PROD_ID]
            product = Product.objects.get(id=initial_id)
            initial_name = product.name
            initial_price = product.price
        if KW_PROD_TYPE_ID in kwargs:
            initial_type_id = kwargs[KW_PROD_TYPE_ID]

        self.fields["id"] = forms.CharField(
            initial=initial_id, widget=forms.HiddenInput()
        )
        self.fields["type_id"] = forms.CharField(
            initial=initial_type_id, widget=forms.HiddenInput()
        )
        self.fields["name"] = forms.CharField(
            initial=initial_name, required=True, label=_("Produkt Name")
        )
        self.fields["price"] = forms.FloatField(
            initial=initial_price, required=True, label=_("Preis")
        )


class GrowingPeriodForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(GrowingPeriodForm, self).__init__(*args)

        today = datetime.date.today()
        initial = {
            "id": "-",
            "start_date": today + relativedelta(days=1),
            "end_date": today + relativedelta(years=1),
        }

        if KW_PERIOD_ID in kwargs:
            period = GrowingPeriod.objects.get(id=kwargs[KW_PERIOD_ID])
            new_start_date = period.end_date + relativedelta(days=1)
            self.update_initial(initial, new_start_date)
            initial["id"] = period.id
        else:
            try:
                period = GrowingPeriod.objects.order_by("-end_date").first()
                new_start_date = period.end_date + relativedelta(days=1)
                self.update_initial(initial, new_start_date)
            except GrowingPeriod.DoesNotExist:
                pass

        self.fields["id"] = forms.CharField(
            initial=initial["id"], required=False, widget=forms.HiddenInput()
        )
        self.fields["start_date"] = forms.DateField(
            required=True,
            label=_("Von"),
            widget=DateInput(),
            initial=initial["start_date"],
        )
        self.fields["end_date"] = forms.DateField(
            required=True,
            label=_("Bis"),
            widget=DateInput(),
            initial=initial["end_date"],
        )

    def is_valid(self):
        super(GrowingPeriodForm, self).is_valid()

        start = self.cleaned_data["start_date"]
        end = self.cleaned_data["end_date"]

        error_field = "start_date"

        try:
            validate_date_range(start_date=start, end_date=end)
        except ValidationError as e:
            self.add_error(field=error_field, error=e)

        try:
            validate_growing_period_overlap(start_date=start, end_date=end)
        except ValidationError as e:
            self.add_error(field=error_field, error=e)

        return not self.has_error(field=error_field)

    def update_initial(self, initial, new_start_date):
        initial.update(
            {
                "start_date": new_start_date,
                "end_date": new_start_date + relativedelta(years=1, days=-1),
            }
        )