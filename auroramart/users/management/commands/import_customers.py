import csv
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from users.models import Customer

User = get_user_model()


class Command(BaseCommand):
	help = 'Import customers from b2c_customers_100.csv'

	def add_arguments(self, parser):
		parser.add_argument(
			'--file',
			type=str,
			default='data/b2c_customers_100.csv',
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
		
		customers_created = 0
		customers_updated = 0
		
		with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
			reader = csv.DictReader(f)
			
			for idx, row in enumerate(reader, start=1):
				# Parse CSV columns
				age = int(row['age'])
				gender = row['gender'].strip().capitalize()
				employment_status = row['employment_status'].strip()
				occupation = row['occupation'].strip()
				education = row['education'].strip()
				household_size = int(row['household_size'])
				has_children = bool(int(row['has_children']))
				monthly_income_sgd = Decimal(row['monthly_income_sgd'])
				preferred_category = row['preferred_category'].strip()
				
				# Normalize employment status to match model choices
				employment_map = {
					'full-time': 'Full-Time',
					'part-time': 'Part-Time',
					'self-employed': 'Self-Employed',
					'student': 'Student',
					'retired': 'Retired',
				}
				employment_status = employment_map.get(employment_status.lower(), employment_status)
				
				# Create username
				username = f'customer{idx:03d}'
				
				# Create or get user
				user, user_created = User.objects.get_or_create(
					username=username,
					defaults={
						'email': f'{username}@auroramart.com',
						'first_name': 'Customer',
						'last_name': f'{idx}',
					}
				)
				
				# Set password if new user
				if user_created:
					user.set_password('password123')
					user.save()
				
				# Create or update customer profile
				customer, created = Customer.objects.update_or_create(
					user=user,
					defaults={
						'age': age,
						'gender': gender,
						'employment_status': employment_status,
						'occupation': occupation,
						'education': education,
						'household_size': household_size,
						'has_children': has_children,
						'monthly_income_sgd': monthly_income_sgd,
						'preferred_category': preferred_category,
					}
				)
				
				if created:
					customers_created += 1
				else:
					customers_updated += 1
		
		self.stdout.write(self.style.SUCCESS(
			f'\nImport completed successfully!\n'
			f'Customers created: {customers_created}\n'
			f'Customers updated: {customers_updated}'
		))
