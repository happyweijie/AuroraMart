from django.core.management.base import BaseCommand
from admin_panel.models import RecommendationPlacement


class Command(BaseCommand):
    help = 'Seed recommendation placement configurations'

    def handle(self, *args, **options):
        placements = [
            {
                'slug': 'homepage_trending',
                'placement': 'homepage',
                'title': 'Homepage Trending Products',
                'strategy': 'association_rules',
                'is_active': True,
            },
            {
                'slug': 'product_detail_also_bought',
                'placement': 'product_detail',
                'title': 'Customers Also Bought',
                'strategy': 'association_rules',
                'is_active': True,
            },
            {
                'slug': 'cart_upsell',
                'placement': 'cart',
                'title': 'Cart Upsell Recommendations',
                'strategy': 'association_rules',
                'is_active': True,
            },
            {
                'slug': 'category_explore',
                'placement': 'category',
                'title': 'Explore Similar Products',
                'strategy': 'decision_tree',
                'is_active': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for placement_data in placements:
            placement, created = RecommendationPlacement.objects.update_or_create(
                slug=placement_data['slug'],
                defaults=placement_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created placement: {placement.slug}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated placement: {placement.slug}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} placements, updated {updated_count} placements.'
            )
        )

