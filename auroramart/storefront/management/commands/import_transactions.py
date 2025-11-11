import csv
import os
from decimal import Decimal
from datetime import datetime, timedelta
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from storefront.models import Product, Order, OrderItem
from users.models import Customer


class Command(BaseCommand):
	help = 'Import transactions from b2c_products_500_transactions_50k.csv and create orders'

	def add_arguments(self, parser):
		parser.add_argument(
			'--file',
			type=str,
			default='data/b2c_products_500_transactions_50k.csv',
			help='Path to the transactions CSV file relative to project root'
		)
		parser.add_argument(
			'--limit',
			type=int,
			default=None,
			help='Limit the number of transactions to import (useful for testing)'
		)
		parser.add_argument(
			'--clear',
			action='store_true',
			help='Clear all existing orders before importing'
		)

	@transaction.atomic
	def handle(self, *args, **options):
		csv_file = options['file']
		limit = options['limit']
		clear_existing = options['clear']
		
		# Get the project root
		base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
		file_path = os.path.join(base_dir, '..', csv_file)
		
		if not os.path.exists(file_path):
			self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
			return
		
		self.stdout.write(self.style.SUCCESS(f'Reading from: {file_path}'))
		
		# Clear existing orders if requested
		if clear_existing:
			order_count = Order.objects.count()
			if order_count > 0:
				self.stdout.write(self.style.WARNING(f'Deleting {order_count} existing orders...'))
				Order.objects.all().delete()
				self.stdout.write(self.style.SUCCESS('Existing orders deleted'))
		else:
			# Check if orders already exist
			existing_orders = Order.objects.count()
			if existing_orders > 0:
				self.stdout.write(self.style.WARNING(
					f'Found {existing_orders} existing orders. '
					f'Use --clear flag to delete them before importing.'
				))
				self.stdout.write('Skipping import to avoid duplicates.')
				return
		
		# Get all customers
		customers = list(Customer.objects.all())
		if len(customers) == 0:
			self.stdout.write(self.style.ERROR('No customers found. Please import customers first.'))
			return
		
		self.stdout.write(f'Found {len(customers)} customers')
		
		# Get all products ordered by ID to match CSV column order
		products = list(Product.objects.all().order_by('id'))
		
		if len(products) == 0:
			self.stdout.write(self.style.ERROR('No products found. Please import products first.'))
			return
		
		self.stdout.write(f'Found {len(products)} products')
		
		orders_created = 0
		order_items_created = 0
		empty_baskets = 0
		
		# Start date for orders (spread over last 6 months)
		start_date = datetime.now() - timedelta(days=180)
		
		with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
			reader = csv.reader(f)
			header = next(reader)  # Skip header (product SKUs)
			
			self.stdout.write(f'CSV has {len(header)} product columns')
			
			for row_num, row in enumerate(reader, start=1):
				if limit and row_num > limit:
					break
				
				# Parse the basket (binary values: 1 = product in basket, 0 = not)
				basket = []
				for val in row:
					if val.strip():
						basket.append(int(val))
					else:
						basket.append(0)
				
				# Find products in this basket
				products_in_basket = []
				for idx, quantity in enumerate(basket):
					if quantity > 0 and idx < len(products):
						products_in_basket.append((products[idx], quantity))
				
				if not products_in_basket:
					empty_baskets += 1
					continue
				
				# Randomly assign to a customer
				customer = random.choice(customers)
				
				# Create order with a timestamp spread over 6 months
				days_ago = random.randint(0, 180)
				order_date = start_date + timedelta(days=days_ago)
				
				# Randomly assign order status (most completed)
				status = random.choices(
					['delivered', 'shipped', 'processing', 'pending'],
					weights=[70, 15, 10, 5],
					k=1
				)[0]
				
				order = Order.objects.create(
					customer=customer,
					status=status,
					created_at=order_date,
					shipping_address=f'{random.randint(1, 999)} Main Street, Singapore {random.randint(100000, 999999)}'
				)
				
				# Create order items
				total_price = Decimal('0.00')
				for product, quantity in products_in_basket:
					unit_price = product.price
					OrderItem.objects.create(
						order=order,
						product=product,
						quantity=quantity,
						unit_price=unit_price
					)
					total_price += unit_price * quantity
					order_items_created += 1
				
				# Update order total
				order.total_price = total_price
				order.save()
				
				orders_created += 1
				
				if orders_created % 1000 == 0:
					self.stdout.write(f'Processed {orders_created} orders...')
		
		self.stdout.write(self.style.SUCCESS(
			f'\nImport completed successfully!\n'
			f'Orders created: {orders_created}\n'
			f'Order items created: {order_items_created}\n'
			f'Empty baskets skipped: {empty_baskets}\n'
			f'Average items per order: {order_items_created / orders_created if orders_created > 0 else 0:.2f}'
		))
