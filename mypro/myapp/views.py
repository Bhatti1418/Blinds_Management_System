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
from django.urls import reverse
from django.db.models import Sum
from django.contrib.auth.decorators import login_required



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

@login_required(login_url='myapp:login')
def homepage(request):
    blinds = Blind.objects.all()

    # Totals
    pending_orders_amount = TransactionItem.objects.filter(
        transaction__payment_status="Pending"
    ).aggregate(total=Sum('total_price'))['total'] or 0

    total_blinds_amount = Blind.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    sold_blinds_amount = TransactionItem.objects.filter(
        transaction__payment_status="Paid"
    ).aggregate(total=Sum('total_price'))['total'] or 0

    return render(request, 'home.html', {
        'blinds': blinds,

        # Raw totals
        'total_blinds': pending_orders_amount,
        'sold_blinds': total_blinds_amount,
        'pending_orders': sold_blinds_amount,

        # Short format display (K, M, B)
        'total_blinds_display': format_large_numbers(pending_orders_amount),
        'sold_blinds_display': format_large_numbers(total_blinds_amount),
        'pending_orders_display': format_large_numbers(sold_blinds_amount),

        # Exact format (comma, 2 decimal)
        'total_blinds_exact': f"{pending_orders_amount:,.2f}",
        'sold_blinds_exact': f"{total_blinds_amount:,.2f}",
        'pending_orders_exact': f"{sold_blinds_amount:,.2f}",
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
            item.length = float(request.POST.get(f'length_{item.id}', item.length))
            item.width = float(request.POST.get(f'width_{item.id}', item.width))
            item.price = float(request.POST.get(f'price_{item.id}', item.price))
            item.square_foot = (item.length / 12) * (item.width / 12)
            if item.square_foot < 16:
                item.square_foot = 16
            item.total_price = item.square_foot * item.price
            item.save()

        # Update Blind stats
        blinds = set(item.blind for item in items)
        for blind in blinds:
            related_items = TransactionItem.objects.filter(blind=blind)
            blind.total_square_foot = sum(item.square_foot for item in related_items)
            blind.total_amount = sum(item.total_price for item in related_items)
            blind.remaining_quantity = blind.blind_quantity - blind.total_square_foot
            blind.save()

        # Update Transaction totals
        all_items_in_transaction = TransactionItem.objects.filter(transaction=transaction)
        transaction.total_prc = sum(item.total_price for item in all_items_in_transaction)
        transaction.total_sq_ft = sum(item.square_foot for item in all_items_in_transaction)
        transaction.total_balance = transaction.total_prc
        transaction.remaining_balance = transaction.total_balance - transaction.receiving_balance
        transaction.save()

        # ✅ Determine source page from query param
        source = request.GET.get('source', '')

        if source == 'balance':
            return redirect(
                f"{reverse('myapp:balance')}?clientname={transaction.client.person_name}&highlight_id={transaction.id}"
            )
        else:
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

        # Get or create client
        client, _ = Client.objects.get_or_create(
            person_name=c_name,
            defaults={'user': User.objects.first()}
        )

        blinds_to_buy, invalid_items, out_of_stock = [], [], []

        for blind_data in data.get('blinds', []):
            b_name = blind_data.get('blindName', '').strip()
            width = float(blind_data.get('length', 0))
            print("width: ",width)
            length = float(blind_data.get('width', 0))
            sq_ft = (width / 12) * (length / 12)
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

            # Update blind inventory
            blind_obj.remaining_quantity -= sq_ft
            blind_obj.total_square_foot += sq_ft
            blind_obj.total_amount += total_price
            blind_obj.purchased_count += 1
            blind_obj.save()

            blinds_to_buy.append(TransactionItem(
                transaction=None,  # set later
                blind=blind_obj,
                length=length,
                width=width,
                square_foot=sq_ft,
                price=blind_obj.blind_price,
                total_price=total_price
            ))

        if not blinds_to_buy:
            return JsonResponse({
                'invalid_blinds': invalid_items,
                'out_of_stock': out_of_stock
            }, status=400)

        # ✅ Calculate totals BEFORE creating transaction
        total_price = sum(item.total_price for item in blinds_to_buy)
        total_sq_ft = sum(item.square_foot for item in blinds_to_buy)
        receiving_balance = 0  # or use your logic if user enters an amount

        # ✅ Create transaction with all required fields
        transaction = Transaction.objects.create(
            client=client,
            total_prc=total_price,
            total_sq_ft=total_sq_ft,
            total_balance=total_price,
            receiving_balance=receiving_balance,
            remaining_balance=total_price - receiving_balance
        )

        # ✅ Attach transaction to each item
        for item in blinds_to_buy:
            item.transaction = transaction
        TransactionItem.objects.bulk_create(blinds_to_buy)

        return JsonResponse({
            "redirect_url": f"{reverse('myapp:balance')}?clientname={client.person_name}&highlight_id={transaction.id}"
        })


    except json.JSONDecodeError:
        return JsonResponse({'error': "Invalid JSON data"}, status=400)

    except Exception as e:
        return JsonResponse({'error': f"Unexpected error occurred: {str(e)}"}, status=500)


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
    just_completed = None

    client_name = request.POST.get("clientname", "").strip().upper() if request.method == 'POST' else request.GET.get("clientname", "").strip().upper()
    highlight_id = request.GET.get("highlight_id")

    # 🧠 If highlight_id in GET, store in session
    if highlight_id:
        request.session['highlight_id'] = highlight_id
    # 🧠 If not in GET, try to get from session
    elif not highlight_id and 'highlight_id' in request.session:
        highlight_id = request.session['highlight_id']

    if request.method == 'POST':
        receiving_amount_str = request.POST.get("receivingamount", "").replace(",", "")
        try:
            receiving_amount = float(receiving_amount_str)
        except ValueError:
            receiving_amount = 0
        if receiving_amount > 0 and client_name:
            if 'receiving_amounts' not in request.session:
                request.session['receiving_amounts'] = {}
            if client_name not in request.session['receiving_amounts']:
                request.session['receiving_amounts'][client_name] = []

            request.session['receiving_amounts'][client_name].append({
                "date": str(datetime.today().date()),
                "amount": receiving_amount
            })
            request.session.modified = True

    if client_name:
        request.session['client_name'] = client_name
        transactions_qs = Transaction.objects.filter(client__person_name__iexact=client_name)

        if transactions_qs.exists():
            for transaction in transactions_qs:
                transaction_total = sum(item.total_price for item in transaction.transactionitem_set.all())
                total_balance += transaction_total

                transactions.append({
                    'id': transaction.id,
                    'date': transaction.created_at.date(),
                    'debit': transaction_total,
                    'credit': 0,
                    'balance': None,
                    'highlight': str(transaction.id) == highlight_id
                })

                # After fetching transactions_qs
                highlighted_transaction = transactions_qs.filter(id=highlight_id).first()
                if highlighted_transaction:
                    just_completed = {
                        "id": highlighted_transaction.id,
                        "date": highlighted_transaction.created_at,
                        "client": highlighted_transaction.client.person_name,
                        "items": highlighted_transaction.transactionitem_set.all(),
                        "total_price": highlighted_transaction.total_prc,
                        "total_sqft": highlighted_transaction.total_sq_ft,
                        "payment_status": highlighted_transaction.payment_status
                    }

            receiving_entries = request.session.get('receiving_amounts', {}).get(client_name, [])
            for entry in receiving_entries:
                date_obj = datetime.strptime(entry['date'], "%Y-%m-%d").date() if isinstance(entry['date'], str) else entry['date']
                transactions.append({
                    'id': None,
                    'date': date_obj,
                    'debit': 0,
                    'credit': entry['amount'],
                    'balance': None,
                    'highlight': False
                })
                receiving_balance += entry['amount']

            # Sort by date
            transactions.sort(key=lambda x: x['date'])

            # Calculate running balance
            running_balance = 0
            for t in transactions:
                running_balance += t['debit']
                running_balance -= t['credit']
                t['balance'] = running_balance

            remaining_balance = running_balance
        else:
            message = "No transactions found for this client."

    return render(request, 'balance.html', {
        'transactions': transactions,
        'total_balance': f"{total_balance:,.2f}",
        'receiving_balance': f"{receiving_balance:,.2f}",
        'remaining_balance': f"{remaining_balance:,.2f}",
        'client_name': request.session.get('client_name', ''),
        'just_completed': just_completed,
        'message': message
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
        transaction = get_object_or_404(Transaction, id=id)
        payment_status = request.POST.get('payment_status')

        if payment_status not in ['Pending', 'Paid']:
            return HttpResponseBadRequest("Invalid payment status.")

        transaction.payment_status = payment_status

        if payment_status == 'Paid':
            transaction.receiving_balance = transaction.total_balance
            transaction.remaining_balance = 0

        transaction.save()

        # ✅ Smart redirect back to the same page with highlighting
        next_url = request.GET.get('next') or reverse('myapp:balance')
        highlight_id = request.GET.get('highlight_id', transaction.id)
        redirect_url = f"{next_url}?clientname={transaction.client.person_name}&highlight_id={highlight_id}"

        return redirect(redirect_url)

    return redirect('myapp:homepage')



def transactions_view(request):
    highlight_id = request.GET.get("highlight_id")  # Get updated transaction ID

    all_transactions = Transaction.objects.prefetch_related('transactionitem_set').select_related('client').order_by('-created_at')
    paginator = Paginator(all_transactions, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for transaction in page_obj:
        transaction.highlight = str(transaction.id) == str(highlight_id)

    return render(request, 'transaction.html', {
        'page_obj': page_obj,
    })

def generate_bill(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)
    items = transaction.transactionitem_set.all()

    # Local timezone conversion
    local_date = timezone.localtime(transaction.created_at)

    context = {
        'date': local_date.strftime('%d/%m/%Y'),
        'invoice_no': transaction.id,
        'client_name': transaction.client.person_name,
        'items': items,
        'total_price': transaction.total_prc,
        'total_sq_ft': transaction.total_sq_ft,
        'advance': transaction.receiving_balance,
        'balance': transaction.remaining_balance,
    }

    return render(request, 'bill.html', context)


    # Render the bill template
    return render(request, 'bill.html', context)

