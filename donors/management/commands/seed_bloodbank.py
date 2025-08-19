# donors/management/commands/seed_bloodbank.py
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from donors.models import Donor, Donation
from faker import Faker

class Command(BaseCommand):
    help = 'Seeds the blood bank database with 100 donors and multiple donations each'

    def handle(self, *args, **options):
        fake = Faker('he_IL')
        
        # Hebrew names data
        hebrew_data = {
            'male_names': ['דוד', 'משה', 'אברהם', 'יצחק', 'יעקב', 'יוסף', 'דניאל', 'שלמה', 'אריאל'],
            'female_names': ['שרה', 'רחל', 'לאה', 'מרים', 'אסתר', 'חנה', 'תמר', 'יעל', 'נועה'],
            'last_names': ['כהן', 'לוי', 'מזרחי', 'פרץ', 'דוד', 'אשכנזי', 'בן-דוד', 'חדד', 'עמר']
        }
        
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        self.stdout.write(self.style.HTTP_INFO(
            'Creating 100 donors with 3-5 donations each...'
        ))
        
        for i in range(100):  # Create exactly 100 donors
            # Random gender selection
            is_male = random.choice([True, False])
            first_name = random.choice(
                hebrew_data['male_names'] if is_male else hebrew_data['female_names']
            )
            
            # Create donor
            donor = Donor.objects.create(
                national_id=fake.unique.numerify('########'),
                first_name=first_name,
                last_name=random.choice(hebrew_data['last_names']),
                date_of_birth=fake.date_between(start_date='-60y', end_date='-18y'),
                blood_type=random.choice(blood_types),
                phone_number=fake.unique.numerify('+9725########'),
                email=fake.unique.email(),
                smoking_status=random.choice(['never', 'former', 'light', 'heavy']),
                alcohol_use=random.choice(['never', 'social', 'weekly', 'daily']),
            )
            
            # Create 3-5 donations for this donor with realistic spacing
            donation_count = random.randint(3, 5)
            first_donation_date = fake.date_between(start_date='-3y', end_date='-6m')
            
            for j in range(donation_count):
                # Space donations 2-4 months apart
                donation_date = first_donation_date + timedelta(
                    days=random.randint(60, 120) * j
                )
                
                # Ensure donation date isn't in the future
                if donation_date > timezone.now().date():
                    donation_date = timezone.now().date() - timedelta(days=1)
                
                Donation.objects.create(
                    donor=donor,
                    donation_date=donation_date,
                    volume_ml=random.choice([350, 400, 450, 500]),
                    notes=self.generate_hebrew_notes(donor),
                    is_approved=self.determine_approval(donor, j)
                )
            
            # Progress feedback
            self.stdout.write(
                f'\rCreated donor {i+1}/100: {donor} with {donation_count} donations',
                ending=''
            )
            self.stdout.flush()
        
        self.stdout.write(self.style.SUCCESS(
            '\nSuccessfully created 100 donors with 3-5 donations each!'
        ))

    def generate_hebrew_notes(self, donor):
        notes_options = [
            '',
            'תורם מצוין',
            'נדרש מנוחה לפני תרומה נוספת',
            'אין הערות מיוחדות',
            'מגיע באופן קבוע',
            'בעל סוג דם נדיר' if donor.blood_type in ['AB-', 'B-', 'O-'] else '',
            f'תורם מאז {random.randint(2015, 2020)}',
            'מעשן' if donor.smoking_status in ['light', 'heavy'] else ''
        ]
        return random.choice([note for note in notes_options if note])

    def determine_approval(self, donor, donation_index):
        """More likely to approve regular donors and later donations"""
        if donation_index > 1:  # After first two donations
            return random.choices([True, False], weights=[80, 20])[0]
        return random.choices([True, False], weights=[60, 40])[0]