from datetime import datetime, timezone, date

from bootstrap_datepicker_plus.widgets import DatePickerInput
from dateutil.relativedelta import relativedelta
from django.core.validators import (
    EmailValidator,
)
from django.db import transaction
from django.db.models import Sum
from django.forms import (
    Form,
    CheckboxInput,
    ModelForm,
    BooleanField,
    DecimalField,
    CharField,
    ChoiceField,
    IntegerField,
)
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.forms import TapirPhoneNumberField
from tapir.wirgarten.forms.registration import HarvestShareForm
from tapir.wirgarten.forms.registration.bestellcoop import BestellCoopForm
from tapir.wirgarten.forms.registration.chicken_shares import ChickenShareForm
from tapir.wirgarten.models import Payment, Member, ShareOwnership
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    get_subscriptions_in_trial_period,
    get_next_trial_end_date,
    send_cancellation_confirmation_email,
    send_order_confirmation,
)
from tapir.wirgarten.service.products import get_future_subscriptions


class PersonalDataForm(ModelForm):
    n_columns = 2

    def __init__(self, *args, **kwargs):
        can_edit_name_and_birthdate = kwargs.pop("can_edit_name_and_birthdate", True)

        super(PersonalDataForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            if k != "street_2":
                v.required = True

        self.fields["first_name"].disabled = not can_edit_name_and_birthdate
        self.fields["last_name"].disabled = not can_edit_name_and_birthdate
        self.fields["birthdate"].disabled = not can_edit_name_and_birthdate

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "street",
            "street_2",
            "postcode",
            "city",
            "country",
            "birthdate",
        ]
        widgets = {"birthdate": DatePickerInput(options={"format": "DD.MM.YYYY"})}

    phone_number = TapirPhoneNumberField(label=_("Telefon-Nr"))

    def is_valid(self):
        super().is_valid()

        duplicate_email_query = Member.objects.filter(email=self.cleaned_data["email"])
        if self.instance and self.instance.id:
            duplicate_email_query = duplicate_email_query.exclude(id=self.instance.id)

        if duplicate_email_query.exists():
            self.add_error(
                "email", _("Ein Nutzer mit dieser Email Adresse existiert bereits.")
            )

        birthdate = self.cleaned_data["birthdate"]
        today = date.today()
        if birthdate > today or birthdate < (today + relativedelta(years=-120)):
            self.add_error("birthdate", _("Bitte wähle ein gültiges Datum aus."))
        elif birthdate > (today + relativedelta(years=-18)):
            self.add_error(
                "birthdate",
                _(
                    "Du musst mindestens 18 Jahre alt sein um der Genossenschaft beizutreten."
                ),
            )

        return len(self.errors) == 0


class PaymentAmountEditForm(Form):
    def __init__(self, *args, **kwargs):
        super(PaymentAmountEditForm, self).__init__(*args)

        self.mandate_ref_id = kwargs["mandate_ref_id"].replace("~", "/")
        self.payment_due_date = kwargs["payment_due_date"]

        payments = Payment.objects.filter(
            mandate_ref=self.mandate_ref_id,
            due_date=datetime.strptime(self.payment_due_date, "%d.%m.%Y").date(),
        )

        if len(payments) < 1:
            initial = 0.00
        elif len(payments) > 1:
            raise AssertionError("TOO MANY PAYMENTS FOUND!!")  # FIXME
        else:
            self.payment = payments[0]
            initial = self.payment.amount

        self.fields["comment"] = CharField(label=_("Änderungsgrund"), required=True)
        self.fields["amount"] = DecimalField(
            label=_("Neuer Betrag [€]"), initial=round(initial, 2)
        )
        self.fields["security_check"] = BooleanField(
            label=_(
                "Ich weiß was ich tue und bin mir der möglichen Konsequenzen bewusst."
            ),
            required=True,
            initial=False,
        )

    def is_valid(self):
        return (
            self.data["comment"]
            and self.data["security_check"]
            and float(self.data["amount"]) > 0
        )


class CoopShareTransferForm(Form):
    def __init__(self, *args, **kwargs):
        super(CoopShareTransferForm, self).__init__(*args)
        member_id = kwargs["pk"]
        orig_member = Member.objects.get(pk=member_id)
        orig_share_ownership_quantity = ShareOwnership.objects.filter(
            member_id=member_id
        ).aggregate(quantity_sum=Sum("quantity"))["quantity_sum"]

        def member_to_string(m):
            return f"{m.first_name} {m.last_name} ({m.email})"

        choices = map(
            lambda x: (x.id, member_to_string(x)),
            Member.objects.exclude(pk=kwargs["pk"]).order_by(
                "first_name", "last_name", "email"
            ),
        )

        self.fields["origin"] = CharField(
            label=_("Ursprünglicher Anteilseigner")
            + f" ({orig_share_ownership_quantity} Anteile)",
            disabled=True,
            initial=member_to_string(orig_member),
        )
        self.fields["receiver"] = ChoiceField(
            label=_("Empfänger der Genossenschaftsanteile"), choices=choices
        )
        self.fields["quantity"] = IntegerField(
            label=_("Anzahl der Anteile"),
            initial=orig_share_ownership_quantity,
            min_value=1,
            max_value=orig_share_ownership_quantity,
        )
        self.fields["security_check"] = BooleanField(
            label=_("Ich weiß was ich tue und bin mir der Konsequenzen bewusst."),
            required=True,
        )


class WaitingListForm(Form):
    n_columns = 2
    colspans = {"email": 2, "privacy_consent": 2}

    def __init__(self, *args, **kwargs):
        super(WaitingListForm, self).__init__(*args, **kwargs)
        self.fields["first_name"] = CharField(label=_("Vorname"))
        self.fields["last_name"] = CharField(label=_("Nachname"))
        self.fields["email"] = CharField(
            label=_("Email"), validators=[EmailValidator()]
        )
        self.fields["privacy_consent"] = BooleanField(
            label=_("Ja, ich habe die Datenschutzerklärung zur Kenntnis genommen."),
            required=True,
            help_text=_(
                'Wir behandeln deine Daten vertraulich, verwenden diese nur im Rahmen der Mitgliederverwaltung und geben sie nicht an Dritte weiter. Unsere Datenschutzerklärung kannst du hier einsehen: <a target="_blank" href="{privacy_link}">Datenschutzerklärung - {site_name}</a>'
            ).format(
                site_name=get_parameter_value(Parameter.SITE_NAME),
                privacy_link=get_parameter_value(Parameter.SITE_PRIVACY_LINK),
            ),
        )


class TrialCancellationForm(Form):
    KEY_PREFIX = "sub_"
    BASE_PROD_TYPE_ATTR = "data-base-product-type"

    template_name = "wirgarten/member/trial_cancellation_form.html"

    def __init__(self, *args, **kwargs):
        self.member_id = kwargs.pop("pk")
        super(TrialCancellationForm, self).__init__(*args, **kwargs)

        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        self.subs = get_subscriptions_in_trial_period(self.member_id)
        self.next_trial_end_date = get_next_trial_end_date(self.subs[0])

        def is_new_member() -> bool:
            try:
                self.share_ownership = ShareOwnership.objects.get(
                    member_id=self.member_id
                )
                return self.share_ownership.entry_date > self.next_trial_end_date
            except (
                ShareOwnership.DoesNotExist,
                ShareOwnership.MultipleObjectsReturned,
            ):
                return (
                    False  # new members should have exactly one share_ownership entity
                )

        for sub in self.subs:
            key = f"{self.KEY_PREFIX}{sub.id}"
            self.fields[key] = BooleanField(
                label=f"{sub.quantity} × {sub.product.name} {sub.product.type.name}",
                required=False,
            )
            if len(self.subs) > 1 and sub.product.type.id == base_product_type_id:
                self.fields[key].widget = CheckboxInput(
                    attrs={"data-base-product-type": "true"}
                )

        if is_new_member():
            self.fields["cancel_coop"] = BooleanField(
                label="Mitgliedschaftsantrag zurückziehen", required=False
            )

    def is_valid(self):
        all_base_product_types_selected = True
        at_least_one_base_product_type_selected = False
        at_least_one_additional_product_type_selected = False
        for k, v in self.fields.items():
            if k in self.data:
                if self.BASE_PROD_TYPE_ATTR in v.widget.attrs:
                    at_least_one_base_product_type_selected = True
                    all_base_product_types_selected = False
                else:
                    at_least_one_additional_product_type_selected = True

        if (
            not at_least_one_base_product_type_selected
            and not at_least_one_additional_product_type_selected
        ):
            self.add_error(
                list(self.fields.keys())[0],
                _(
                    "Bitte wähle mindestens einen Vertrag aus, oder klick 'Abbrechen' falls du doch nicht kündigen möchtest."
                ),
            )
        elif (
            all_base_product_types_selected
            and not at_least_one_additional_product_type_selected
        ):
            self.add_error(
                list(self.fields.keys())[0],
                _("Du kannst keine Zusatzabos beziehen wenn du das Basisabo kündigst."),
            )

        return not self._errors and super(TrialCancellationForm, self).is_valid()

    @transaction.atomic
    def save(self):
        cancel_coop = "cancel_coop" in self.cleaned_data and self.cleaned_data.pop(
            "cancel_coop"
        )
        subs_to_cancel = self.subs.filter(
            id__in=[
                key.replace("sub_", "")
                for key, value in self.cleaned_data.items()
                if value
            ]
        )
        now = datetime.now(tz=timezone.utc)
        for sub in subs_to_cancel:
            sub.cancellation_ts = now
            sub.end_date = self.next_trial_end_date
            sub.save()

        if cancel_coop and self.share_ownership:
            Payment.objects.get(
                mandate_ref=self.share_ownership.mandate_ref, due_date__gt=now
            ).delete()
            self.share_ownership.delete()  # TODO: create log entry

        send_cancellation_confirmation_email(
            self.member_id, self.next_trial_end_date, subs_to_cancel
        )

        return subs_to_cancel[0].end_date


class SubscriptionRenewalForm(Form):
    template_name = "wirgarten/member/subscription_renewal_form.html"
    n_columns = 4
    colspans = {}

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, **{k: v for k, v in kwargs.items() if k != "start_date"}
        )
        self.start_date = kwargs["start_date"]

        # FIXME: hardcoded product forms :(
        self.product_forms = [
            HarvestShareForm(*args, **kwargs, enable_validation=True),
            ChickenShareForm(*args, **kwargs),
            BestellCoopForm(*args, **kwargs),
        ]
        for form in self.product_forms:
            for field_name, field in form.fields.items():
                self.fields[field_name] = field

    def is_valid(self):
        super().is_valid()
        for form in self.product_forms:
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == "__all__":
                            self.add_error(None, error)
                        else:
                            self.add_error(field, error)

        return len(self.errors) == 0

    @transaction.atomic
    def save(self, *args, **kwargs):
        for form in self.product_forms:
            form.save(*args, **kwargs)

        member_id = kwargs["member_id"]
        subs = get_future_subscriptions(self.start_date).filter(
            member_id=member_id, cancellation_ts__isnull=True
        )

        member = Member.objects.get(id=member_id)
        send_order_confirmation(member, subs)
