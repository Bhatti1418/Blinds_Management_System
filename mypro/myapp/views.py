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
from django.contrib.auth import authenticate, login
from django.core.paginator import Paginator
from django.db.models import Sum

# Homepage view
from django.shortcuts import render
from django.db.models import Sum
from .models import Blind, TransactionItem, Transaction


def mylogin(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('myapp:homepage')
        else:
            return render(request, 'login.html',
                          {'error': 'Invalid username or password'})  # 👈 Re-render with CSRF token
    return render(request, 'login.html')



def format_large_numbers(value):
    """Format large values into human-readable format with M (Million), B (Billion), or standard numbers."""
    if value >= 1_000_000_000:  # For Billions
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:  # For Millions
        return f"{value / 1_000_000:.1f}M"
    # elif value >= 1_000:  # For Thousands
    #     return f"{value / 1_000:.1f}K"
    else:
        return f"{value:,.2f}"  # For smaller values, show with commas and 2 decimal places


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
        'pending_orders': sold_blinds_amount,

        # Formatted (Western-style) versions
        'total_blinds_display': format_large_numbers(pending_orders_amount),
        'sold_blinds_display': format_large_numbers(total_blinds_amount),
        'pending_orders_display': format_large_numbers(sold_blinds_amount),
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

        return redirect('myapp:homepage')

    return render(request, 'add_blind.html')


def update_item(request, pk):
    blind = get_object_or_404(Blind, pk=pk)

    if request.method == 'POST':
        b_name = request.POST.get('blindname')
        new_total_qty = float(request.POST.get('totalquantity'))
        old_total_qty = blind.blind_quantity  # Save old total
        r_qty = float(request.POST.get('remquantity'))  # This will be overwritten below
        price = float(request.POST.get('price'))
        purchased_count = float(request.POST.get('purchasedblind'))
        entry_date_str = request.POST.get('entrydate')
        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()

        # ✅ Automatically adjust remaining quantity
        quantity_diff = new_total_qty - old_total_qty
        new_remaining_qty = blind.remaining_quantity + quantity_diff

        # Prevent negative remaining quantity (just in case)
        if new_remaining_qty < 0:
            new_remaining_qty = 0

        # Update the blind object
        blind.blind_name = b_name
        blind.blind_quantity = new_total_qty
        blind.remaining_quantity = new_remaining_qty
        blind.blind_price = price
        blind.purchased_count = purchased_count
        blind.blind_entry_date = entry_date
        blind.save()

        return redirect(reverse('myapp:homepage'))

    return render(request, 'updating_form.html', {'obj': blind})



def update_transaction_item(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    items = TransactionItem.objects.filter(transaction=transaction)

    if request.method == 'POST':
        for item in items:
            # Update individual fields from form data
            item.length = float(request.POST.get(f'length_{item.id}', item.length))
            item.width = float(request.POST.get(f'width_{item.id}', item.width))
            item.price = float(request.POST.get(f'price_{item.id}', item.price))
            item.square_foot = (item.length / 12) * (item.width / 12)
            if item.square_foot < 16:
                item.square_foot = 16
            item.total_price = item.square_foot * item.price
            item.save()

        # Now update Blind and Transaction objects
        blinds = set(item.blind for item in items)

        for blind in blinds:
            related_items = TransactionItem.objects.filter(blind=blind)
            blind.total_square_foot = sum(item.square_foot for item in related_items)
            blind.total_amount = sum(item.total_price for item in related_items)
            blind.remaining_quantity = blind.blind_quantity - blind.total_square_foot
            blind.save()

        # Update transaction totals
        all_items_in_transaction = TransactionItem.objects.filter(transaction=transaction)
        transaction.total_balance = sum(item.total_price for item in all_items_in_transaction)
        transaction.remaining_balance = transaction.total_balance - transaction.receiving_balance
        transaction.save()

        return redirect('myapp:transactions')

    return render(request, 'updating_transaction.html', {'transaction': transaction, 'items': items})




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
            b_name, width,length  = blind_data.get('blindName', '').strip(), float(blind_data.get('length', 0)), float(blind_data.get('width', 0))
            sq_ft = (length/12) * (width/12)
            if sq_ft < 16:
                sq_ft = 16
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
        transaction = Transaction.objects.create(client=client)  # The date field is automatically set
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


def format_large_numbers(value):
    """Format large values into human-readable format with M (Million), B (Billion), or standard numbers."""
    if value >= 1_000_000_000:  # For Billions
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:  # For Millions
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:  # For Thousands
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:,.2f}"  # For smaller values, show with commas and 2 decimal places


def balance_view(request):
    transactions = []
    total_balance = 0
    receiving_balance = 0
    remaining_balance = 0
    message = None

    if request.method == 'POST':
        client_name = request.POST.get("clientname", "").strip().upper()
        receiving_amount_str = request.POST.get("receivingamount", "").strip()
        receiving_amount = 0

        if receiving_amount_str:
            try:
                receiving_amount = float(receiving_amount_str.replace(',', ''))
            except ValueError:
                message = "Invalid receiving amount format."

        if client_name:
            request.session['client_name'] = client_name
            request.session.modified = True

            transactions_qs = Transaction.objects.filter(Q(client__person_name__icontains=client_name))

            if transactions_qs.exists():
                transactions = []

                # --- Get total debits from transaction items ---
                for transaction in transactions_qs:
                    transaction_total = sum(item.total_price for item in transaction.transactionitem_set.all())
                    total_balance += transaction_total
                    transactions.append({
                        'date': timezone.localtime(transaction.created_at).date(),
                        'debit': transaction_total,
                        'credit': 0,
                        'balance': None
                    })

                # --- Initialize session receiving amounts if not exist ---
                if 'receiving_amounts' not in request.session:
                    request.session['receiving_amounts'] = {}
                if client_name not in request.session['receiving_amounts']:
                    request.session['receiving_amounts'][client_name] = []

                # --- Save current receiving amount if > 0 ---
                if receiving_amount > 0:
                    request.session['receiving_amounts'][client_name].append({
                        'amount': receiving_amount,
                        'date': str(timezone.localtime(timezone.now()).date())
                    })
                    request.session.modified = True

                # --- Load all receiving entries for this client ---
                receiving_entries = request.session['receiving_amounts'][client_name]

                # Normalize all entries
                normalized_entries = []
                for entry in receiving_entries:
                    if isinstance(entry, dict):
                        normalized_entries.append(entry)
                    else:
                        normalized_entries.append({
                            'amount': entry,
                            'date': str(timezone.localtime(timezone.now()).date())
                        })

                # Add receiving entries to transaction list
                for entry in normalized_entries:
                    date_obj = entry['date']
                    if isinstance(date_obj, str):
                        date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()

                    transactions.append({
                        'date': date_obj,
                        'debit': 0,
                        'credit': entry['amount'],
                        'balance': None
                    })
                    receiving_balance += entry['amount']

                # --- Sort all transactions by date ---
                transactions.sort(key=lambda x: x['date'])

                # --- Calculate running balance ---
                running_balance = 0
                for t in transactions:
                    running_balance += t['debit']
                    running_balance -= t['credit']
                    t['balance'] = running_balance

                remaining_balance = running_balance

            else:
                message = "No transactions found for this client."
        else:
            message = "Please enter a client name to search."

    # Get client name again for form pre-fill
    client_name = request.session.get('client_name', '')

    # Format balances for display
    formatted_total_balance = f"{total_balance:,.2f}"
    formatted_receiving_balance = f"{receiving_balance:,.2f}"
    formatted_remaining_balance = f"{remaining_balance:,.2f}"

    return render(request, 'balance.html', {
        'transactions': transactions,
        'total_balance': formatted_total_balance,
        'receiving_balance': formatted_receiving_balance,
        'remaining_balance': formatted_remaining_balance,
        'message': message,
        'client_name': client_name
    })


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

        # If paid, set receiving_balance and remaining_balance accordingly
        if payment_status == 'Paid':
            transaction.receiving_balance = transaction.total_balance
            transaction.remaining_balance = 0

        transaction.save()

        # If paid, redirect to balance view
        if payment_status == 'Paid':
            # Pass client name in session for balance view (if needed)
            request.session['client_name'] = transaction.client.person_name.upper()
            return redirect(reverse('myapp:balance'))

    # If not paid or other case, redirect to homepage
    return redirect('myapp:homepage')


def transactions_view(request):
    all_transactions = Transaction.objects.prefetch_related('transactionitem_set').select_related('client').order_by('-created_at')
    paginator = Paginator(all_transactions, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'transaction.html', {'page_obj': page_obj})

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

