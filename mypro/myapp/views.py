from datetime import datetime  # Import datetime to handle date parsing
from .models import Blind
from django.shortcuts import render, redirect
from email.policy import default
import json
from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Client, Blind, Transaction, User, TransactionItem
from collections import defaultdict
from datetime import datetime
from django.db.models import F
from itertools import groupby
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum

# Homepage view
from django.shortcuts import render
from django.db.models import Sum
from .models import Blind, TransactionItem, Transaction

def homepage(request):
    blinds = Blind.objects.all()
    # Sum of total_price for all pending transactions
    pending_orders_amount = TransactionItem.objects.filter(
        transaction__payment_status="Pending"
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Sum of total_amount for all blinds
    total_blinds_amount = Blind.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # Sum of total_price for all completed (Paid) transactions
    sold_blinds_amount = TransactionItem.objects.filter(
        transaction__payment_status="Paid"
    ).aggregate(total=Sum('total_price'))['total'] or 0

    return render(request, 'home.html', {
        'blinds': blinds,
        'total_blinds': pending_orders_amount,
        'sold_blinds': total_blinds_amount,
        'pending_orders': sold_blinds_amount
    })

# Add a new blind
def addblind(request):
    if request.method == 'POST':
        # Retrieve form data
        b_name = request.POST['blindname']
        quantity = float(request.POST['quantity'])
        price = float(request.POST['price'])
        # Get the entry date as a string
        entry_date_str = request.POST['entry_date']

        # Convert the entry date string to a date object
        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()

        # Create and save the new Blind instance
        new_blind = Blind(
            blind_name=b_name,
            blind_quantity=quantity,
            blind_price=price,
            remaining_quantity=quantity,
            blind_entry_date=entry_date  # Add the entry date
        )
        new_blind.save()

        return redirect('/')

    return render(request, 'add_blind.html')




# Update blind details
def update_item(request, pk):
    blind = get_object_or_404(Blind, pk=pk)

    if request.method == 'POST':
        b_name = request.POST.get('blindname')
        t_qty = float(request.POST.get('totalquantity'))
        r_qty = float(request.POST.get('remquantity'))
        price = float(request.POST.get('price'))
        purchased_count = float(request.POST.get('purchasedblind'))
        # Get the entry date as a string
        entry_date_str = request.POST.get('entrydate')

        # Convert the entry date string to a date object
        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()

        # Update the blind object
        blind.blind_name = b_name
        blind.blind_quantity = t_qty
        blind.remaining_quantity = r_qty
        blind.blind_price = price
        blind.purchased_count = purchased_count
        blind.blind_entry_date = entry_date  # Update the entry date
        blind.save()

        return redirect(reverse('myapp:homepage'))

    return render(request, 'updating_form.html', {'obj': blind})


def get_sales_data(request):
    return JsonResponse({
        'clients': list(Client.objects.values_list('person_name', flat=True)),
        'blinds': list(Blind.objects.values_list('blind_name', flat=True))
    })

def sellblind(request):
    if request.method != 'POST':
        return render(request, 'sell_blind.html')

    try:
        data = json.loads(request.body)
        c_name = data.get('clientName', '').strip()

        if not c_name:
            return JsonResponse({'error': "Client name is required."}, status=400)

        # Ensure client exists
        client, _ = Client.objects.get_or_create(
            person_name=c_name,
            defaults={'user': User.objects.first()}
        )

        blinds_to_buy, invalid_items, out_of_stock = [], [], []
        print(f"All blinds: {data.get('blinds')}")

        for blind_data in data.get('blinds', []):
            b_name, length, width = blind_data.get('blindName', '').strip(), float(blind_data.get('length', 0)), float(blind_data.get('width', 0))
            sq_ft = length * width

            blind_obj = Blind.objects.filter(blind_name__iexact=b_name).first()
            if not blind_obj:
                invalid_items.append(blind_data)
                continue

            if blind_obj.remaining_quantity < sq_ft:
                out_of_stock.append(blind_data)
                continue

            total_price = sq_ft * blind_obj.blind_price

            # Update Blind Inventory
            blind_obj.remaining_quantity -= sq_ft
            blind_obj.total_square_foot += sq_ft
            blind_obj.total_amount += total_price
            blind_obj.purchased_count += 1
            blind_obj.save()

            print(blind_data)

            blinds_to_buy.append(TransactionItem(
                transaction=None,  # Set later
                blind=blind_obj,
                length=length,
                width=width,
                square_foot=sq_ft,
                price=blind_obj.blind_price,
                total_price=total_price
            ))

        if not blinds_to_buy:
            return JsonResponse({'invalid_blinds': invalid_items, 'out_of_stock': out_of_stock}, status=400)

        # Create transaction & transaction items
        transaction = Transaction.objects.create(client=client)
        for item in blinds_to_buy:
            item.transaction = transaction
        TransactionItem.objects.bulk_create(blinds_to_buy)
        return JsonResponse({"redirect_url": "/transactions/"})

    except json.JSONDecodeError:
        return JsonResponse({'error': "Invalid JSON data"}, status=400)


def get_blind_quantity(request):
    blind_name = request.GET.get('blind_name')
    blind = Blind.objects.filter(blind_name__iexact=blind_name).first()
    if blind:
        return JsonResponse({'remaining_quantity': blind.remaining_quantity})
    else:
        return JsonResponse({'error': 'Blind not found'}, status=404)


# Search blinds by name
def searchblind(request):
    blinds = None
    message = None

    if request.method == 'POST':
        b_name = request.POST.get("blindname", "").strip()

        if b_name:
            blinds = Blind.objects.filter(Q(blind_name__icontains=b_name))
            if not blinds.exists():
                message = "No blind found."
        else:
            message = "Please enter a blind name to search."

    return render(request, 'search_blind.html', {'blinds': blinds, 'message': message})


def searchtransaction(request):
    transactions = None
    message = None

    if request.method == 'POST':
        client_name = request.POST.get("clientname", "").strip()

        if client_name:
            transactions = Transaction.objects.filter(Q(client__person_name__icontains=client_name))
            if not transactions.exists():
                message = "No transactions found for this client."
        else:
            message = "Please enter a client name to search."

    return render(request, 'searchtransaction.html', {'transactions': transactions, 'message': message})



def update_payment_status(request, id):
    if request.method == 'POST':
        # Get the transaction by id
        transaction = get_object_or_404(Transaction, id=id)

        # Get the new payment status from the form
        payment_status = request.POST.get('payment_status')

        # Validate the payment status
        if payment_status not in ['Pending', 'Paid']:
            return HttpResponseBadRequest("Invalid payment status.")

        # Update the payment status
        transaction.payment_status = payment_status
        transaction.save()

    # Redirect back to the searchtransaction page after updating the status
    return redirect('myapp:homepage')


def transactions_view(request):
    transactions = Transaction.objects.prefetch_related('transactionitem_set').select_related('client')
    return render(request, 'transaction.html', {'transactions': transactions})


def generate_bill(request, transaction_id):
    # Fetch the transaction and related items
    transaction = get_object_or_404(Transaction, id=transaction_id)
    items = transaction.transactionitem_set.all()

    # Calculate the total price
    total = sum(item.total_price for item in items)

    # Convert the transaction date to the local timezone
    local_date = timezone.localtime(transaction.created_at)

    # Prepare context for the template
    context = {
        'date': local_date.strftime('%d/%m/%Y'),  # Use local time
        'invoice_no': transaction.id,
        'client_name': transaction.client.person_name,
        'items': items,
        'total': total,
    }

    # Render the bill template
    return render(request, 'bill.html', context)

