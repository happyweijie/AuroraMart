import csv
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from storefront.models import Category, Product


class Command(BaseCommand):
	help = 'Import products and categories from b2c_products_500.csv'

	def add_arguments(self, parser):
		parser.add_argument(
			'--file',
			type=str,
			default='data/b2c_products_500.csv',
			help='Path to the CSV file relative to project root'
		)

	def handle(self, *args, **options):
		csv_file = options['file']
		
		# Get the project root (parent of auroramart directory)
		base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
		file_path = os.path.join(base_dir, '..', csv_file)
		
		if not os.path.exists(file_path):
			self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
			return
		
		self.stdout.write(self.style.SUCCESS(f'Reading from: {file_path}'))
		
		categories_created = 0
		products_created = 0
		products_updated = 0
		
		with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
			reader = csv.DictReader(f)
			
			for row in reader:
				# Parse CSV columns
				sku = row['SKU code'].strip()
				name = row['Product name'].strip()
				description = row['Product description'].strip()
				category_name = row['Product Category'].strip()
				subcategory_name = row['Product Subcategory'].strip() if row['Product Subcategory'].strip() else None
				stock = int(row['Quantity on hand'])
				reorder_threshold = int(row['Reorder Quantity'])
				price = Decimal(row['Unit price'])
				rating = Decimal(row['Product rating'])
				
				# Create or get main category
				category, created = Category.objects.get_or_create(
					name=category_name,
					defaults={'slug': slugify(category_name)}
				)
				if created:
					categories_created += 1
					self.stdout.write(f'Created category: {category_name}')
				
				# Create or get subcategory if it exists
				if subcategory_name:
					subcategory, created = Category.objects.get_or_create(
						name=subcategory_name,
						defaults={
							'slug': slugify(subcategory_name),
							'parent': category
						}
					)
					if created:
						categories_created += 1
						self.stdout.write(f'Created subcategory: {subcategory_name}')
					# Use subcategory for product
					product_category = subcategory
				else:
					product_category = category
				
				# Create or update product
				product, created = Product.objects.update_or_create(
					sku=sku,
					defaults={
						'name': name,
						'description': description,
						'category': product_category,
						'price': price,
						'rating': rating,
						'stock': stock,
						'reorder_threshold': reorder_threshold,
						'is_active': True,
						'archived': False,
					}
				)
				
				if created:
					products_created += 1
				else:
					products_updated += 1
		
		self.stdout.write(self.style.SUCCESS(
			f'\nImport completed successfully!\n'
			f'Categories created: {categories_created}\n'
			f'Products created: {products_created}\n'
			f'Products updated: {products_updated}'
		))
