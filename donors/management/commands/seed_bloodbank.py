# donors/management/commands/seed_bloodbank.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from donors.models import Donor, Donation, BloodRequest, Profile
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Seeds the database with doctors, patients, donors, donations, and blood requests (Hebrew names)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('🌱 מתחיל את מילוי הנתונים...'))
        
        # Reset everything
        self.stdout.write('🗑️  מוחק נתונים קיימים...')
        User.objects.all().delete()  # This will cascade to related objects
        
        users_data = []
        doctors_data = []
        patients_data = []
        
        # ==============================
        # CREATE DOCTORS (10) - Hebrew Names
        # ==============================
        self.stdout.write('👨‍⚕️ יוצר 10 רופאים...')
        
        doctor_names = [
            ('ד"ר שרה', 'כהן'),
            ('ד"ר משה', 'לוי'),
            ('ד"ר רחל', 'מזרחי'),
            ('ד"ר יצחק', 'פרץ'),
            ('ד"ר מרים', 'גולדברג'),
            ('ד"ר יוסף', 'בן-דוד'),
            ('ד"ר חנה', 'אברמסון'),
            ('ד"ר אברהם', 'שלום'),
            ('ד"ר תמר', 'פרידמן'),
            ('ד"ר אלי', 'וייס')
        ]
        
        for i, (first_name, last_name) in enumerate(doctor_names, 1):
            username = f"doctor{i}"
            password = f"doctor{i}pass"
            email = f"doctor{i}@hospital.com"
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            Profile.objects.create(
                user=user,
                role='doctor',
                phone_number=f'+9725012345{i:02d}'
            )
            
            doctors_data.append({
                'username': username,
                'password': password,
                'name': f'{first_name} {last_name}',
                'type': 'רופא'
            })
            
            self.stdout.write(f'✅ רופא נוצר: {username} / {password}')
        
        # ==============================
        # CREATE PATIENTS (15) - Hebrew Names
        # ==============================
        self.stdout.write('🏥 יוצר 15 מטופלים...')
        
        patient_names = [
            ('דניאל', 'שварץ'), ('לאה', 'וילסון'), ('יעקב', 'בראון'),
            ('רבקה', 'טיילור'), ('שמואל', 'אנדרסון'), ('אסתר', 'תומאס'),
            ('אברהם', 'ג\'קסון'), ('רחל', 'וייט'), ('בנימין', 'האריס'),
            ('יעל', 'מרטין'), ('יוסף', 'תומפסון'), ('סבינה', 'גרסיה'),
            ('יצחק', 'מרטינס'), ('נועה', 'רובינסון'), ('אלעזר', 'קלארק')
        ]
        
        for i, (first_name, last_name) in enumerate(patient_names, 1):
            username = f"patient{i}"
            password = f"patient{i}pass"
            email = f"patient{i}@gmail.com"
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            Profile.objects.create(
                user=user,
                role='patient',
                phone_number=f'+9725212345{i:02d}'
            )
            
            patients_data.append({
                'username': username,
                'password': password,
                'name': f'{first_name} {last_name}',
                'type': 'מטופל'
            })
            
            self.stdout.write(f'✅ מטופל נוצר: {username} / {password}')
        
        # ==============================
        # CREATE DONORS (Mix of Doctors & Patients)
        # ==============================
        self.stdout.write('🩸 יוצר 8 תורמים (שילוב של רופאים ומטופלים)...')
        
        # Get some doctors to be donors
        doctor_users = User.objects.filter(profile__role='doctor')
        patient_users = User.objects.filter(profile__role='patient')
        
        # Make first 3 doctors also donors
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        donor_count = 0
        for doctor_user in doctor_users[:3]:
            national_id = f"1234567{donor_count + 1:02d}"
            
            donor = Donor.objects.create(
                user=doctor_user,
                national_id=national_id,
                first_name=doctor_user.first_name.replace('ד"ר ', ''),
                last_name=doctor_user.last_name,
                date_of_birth=date(1970 + donor_count, 1, 1),
                blood_type=random.choice(blood_types),
                phone_number=doctor_user.profile.phone_number,
                email=doctor_user.email,
                smoking_status='never',
                alcohol_use='never'
            )
            
            users_data.append({
                'username': doctor_user.username,
                'password': f"{doctor_user.username}pass",
                'name': doctor_user.get_full_name(),
                'type': 'רופא ותורם',
                'national_id': national_id
            })
            
            donor_count += 1
        
        # Make first 5 patients also donors
        for patient_user in patient_users[:5]:
            national_id = f"9876543{donor_count + 1:02d}"
            
            donor = Donor.objects.create(
                user=patient_user,
                national_id=national_id,
                first_name=patient_user.first_name,
                last_name=patient_user.last_name,
                date_of_birth=date(1980 + donor_count, 1, 1),
                blood_type=random.choice(blood_types),
                phone_number=patient_user.profile.phone_number,
                email=patient_user.email,
                smoking_status=random.choice(['never', 'light']),
                alcohol_use=random.choice(['never', 'social'])
            )
            
            users_data.append({
                'username': patient_user.username,
                'password': f"{patient_user.username}pass",
                'name': patient_user.get_full_name(),
                'type': 'מטופל ותורם',
                'national_id': national_id
            })
            
            donor_count += 1
        
        # ==============================
        # CREATE DONATIONS (2-4 per donor)
        # ==============================
        self.stdout.write('💉 יוצר תרומות לתורמים...')
        
        all_donors = Donor.objects.all()
        donation_count = 0
        
        for donor in all_donors:
            num_donations = random.randint(2, 4)
            
            for i in range(num_donations):
                # Create donation dates going back 3 years
                days_back = random.randint(30, 1000)
                donation_date = date.today() - timedelta(days=days_back + (i * 100))
                
                Donation.objects.create(
                    donor=donor,
                    donation_date=donation_date,
                    volume_ml=random.choice([350, 400, 450, 500]),
                    notes=f"תרומה רגילה #{i+1}",
                    is_approved=True
                )
                donation_count += 1
        
        self.stdout.write(f'✅ נוצרו {donation_count} תרומות')
        
        # ==============================
        # CREATE BLOOD REQUESTS
        # ==============================
        self.stdout.write('🩸 יוצר בקשות לדם...')
        
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        patients = User.objects.filter(profile__role='patient')
        
        for i in range(20):  # Create 20 blood requests
            BloodRequest.objects.create(
                patient_name=f"מטופל {(i+1):03d}",
                requested_by=random.choice(patients),
                blood_type_needed=random.choice(blood_types),
                units_needed=random.randint(1, 3),
                priority=random.choice(['normal', 'urgent']),
                emergency=random.choice([True, False]) if i % 4 == 0 else False,
                fulfilled=random.choice([True, False]),
                notes="מקרה דחוף" if random.choice([True, False]) else "העברה שגרתית"
            )
        
        self.stdout.write('✅ נוצרו 20 בקשות לדם')
        
        # ==============================
        # DISPLAY LOGIN CREDENTIALS
        # ==============================
        self.stdout.write('\n' + '='*60)
        self.stdout.write('🔐 פרטי התחברות (השתמשו בפרטים האלה כדי לבדוק את האתר)')
        self.stdout.write('='*60)
        
        # Doctors
        self.stdout.write('\n👨‍⚕️ רופאים:')
        self.stdout.write('-' * 40)
        for doctor in doctors_data:
            self.stdout.write(f"שם משתמש: {doctor['username']} | סיסמה: {doctor['password']} | שם: {doctor['name']}")
        
        # Patients
        self.stdout.write('\n🏥 מטופלים:')
        self.stdout.write('-' * 40)
        for patient in patients_data:
            self.stdout.write(f"שם משתמש: {patient['username']} | סיסמה: {patient['password']} | שם: {patient['name']}")
        
        # Donors (special highlight)
        self.stdout.write('\n🩸 תורמים (רופאים ומטופלים שתרמו):')
        self.stdout.write('-' * 50)
        donor_users = [u for u in users_data if 'תורם' in u['type']]
        for donor in donor_users:
            self.stdout.write(f"שם משתמש: {donor['username']} | סיסמה: {donor['password']} | שם: {donor['name']} | ת.ז.: {donor['national_id']}")
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 מילוי הנתונים הסתיים בהצלחה!'))
        self.stdout.write('🚀 הפעל: python manage.py runserver')
        self.stdout.write('📱 תבדקו עם פרטי הכניסה שלמעלה')
        self.stdout.write('='*60)