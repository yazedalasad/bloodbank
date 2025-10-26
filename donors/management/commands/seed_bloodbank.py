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
        Donation.objects.all().delete()
        BloodRequest.objects.all().delete()
        Donor.objects.all().delete()
        Profile.objects.all().delete()
        User.objects.all().delete()
        
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
                phone_number=f'+972-50-123-45{i:02d}'  # Changed format to avoid duplicates
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
                phone_number=f'+972-52-123-45{i:02d}'  # Changed format to avoid duplicates
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
        self.stdout.write('🩸 יוצר 12 תורמים (שילוב של רופאים ומטופלים)...')
        
        # Get some doctors to be donors
        doctor_users = User.objects.filter(profile__role='doctor')
        patient_users = User.objects.filter(profile__role='patient')
        
        # Blood types distribution - ensure we have O- donors
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        donor_count = 0
        o_negative_donors = []
        
        # Make first 4 doctors also donors
        for doctor_user in doctor_users[:4]:
            national_id = f"1234567{donor_count + 1:02d}"
            
            # Ensure we have at least 2 O- donors
            if donor_count < 2:
                blood_type = 'O-'
                o_negative_donors.append(doctor_user)
            else:
                blood_type = random.choice([bt for bt in blood_types if bt != 'O-'])
            
            donor = Donor.objects.create(
                user=doctor_user,
                national_id=national_id,
                first_name=doctor_user.first_name.replace('ד"ר ', ''),
                last_name=doctor_user.last_name,
                date_of_birth=date(1970 + donor_count, 1, 1),
                blood_type=blood_type,
                phone_number=f'+972-54-123-45{donor_count + 1:02d}',  # Different phone format for donors
                email=doctor_user.email,
                smoking_status='never',
                alcohol_use='never'
            )
            
            users_data.append({
                'username': doctor_user.username,
                'password': f"{doctor_user.username}pass",
                'name': doctor_user.get_full_name(),
                'type': 'רופא ותורם',
                'national_id': national_id,
                'blood_type': blood_type
            })
            
            donor_count += 1
            self.stdout.write(f'✅ תורם רופא נוצר: {doctor_user.username} - {blood_type}')
        
        # Make first 8 patients also donors
        for patient_user in patient_users[:8]:
            national_id = f"9876543{donor_count + 1:02d}"
            
            # Ensure we have at least 4 O- donors total
            if len(o_negative_donors) < 4:
                blood_type = 'O-'
                o_negative_donors.append(patient_user)
            else:
                blood_type = random.choice([bt for bt in blood_types if bt != 'O-'])
            
            donor = Donor.objects.create(
                user=patient_user,
                national_id=national_id,
                first_name=patient_user.first_name,
                last_name=patient_user.last_name,
                date_of_birth=date(1980 + donor_count, 1, 1),
                blood_type=blood_type,
                phone_number=f'+972-55-123-45{donor_count + 1:02d}',  # Different phone format for donors
                email=patient_user.email,
                smoking_status=random.choice(['never', 'light']),
                alcohol_use=random.choice(['never', 'social'])
            )
            
            users_data.append({
                'username': patient_user.username,
                'password': f"{patient_user.username}pass",
                'name': patient_user.get_full_name(),
                'type': 'מטופל ותורם',
                'national_id': national_id,
                'blood_type': blood_type
            })
            
            donor_count += 1
            self.stdout.write(f'✅ תורם מטופל נוצר: {patient_user.username} - {blood_type}')
        
        # ==============================
        # CREATE DONATIONS (Strategic creation for emergency availability)
        # ==============================
        self.stdout.write('💉 יוצר תרומות לתורמים (אסטרטגיה לזמינות בחירום)...')
        
        all_donors = Donor.objects.all()
        donation_count = 0
        
        for donor in all_donors:
            # For O- donors: create only old donations (more than 56 days ago)
            # For other donors: mix of recent and old donations
            if donor.blood_type == 'O-':
                # O- donors get only old donations (60-365 days ago) so they're available
                num_donations = random.randint(1, 2)
                for i in range(num_donations):
                    days_back = random.randint(60, 365)  # More than 56 days
                    donation_date = date.today() - timedelta(days=days_back)
                    
                    Donation.objects.create(
                        donor=donor,
                        donation_date=donation_date,
                        volume_ml=450,
                        notes=f"תרומה רגילה #{i+1}",
                        is_approved=True
                    )
                    donation_count += 1
            else:
                # Other donors get mix of recent and old donations
                num_donations = random.randint(2, 4)
                for i in range(num_donations):
                    if i == 0:
                        # Recent donation (less than 56 days)
                        days_back = random.randint(1, 55)
                    else:
                        # Old donation
                        days_back = random.randint(60, 1000)
                    
                    donation_date = date.today() - timedelta(days=days_back)
                    
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
        self.stdout.write('-' * 60)
        donor_users = [u for u in users_data if 'תורם' in u['type']]
        for donor in donor_users:
            # Check if donor can donate
            donor_obj = Donor.objects.get(national_id=donor['national_id'])
            status = "🟢 זמין" if donor_obj.can_donate else "🔴 לא זמין (תרם לאחרונה)"
            self.stdout.write(f"שם משתמש: {donor['username']} | סיסמה: {donor['password']} | שם: {donor['name']} | ת.ז.: {donor['national_id']} | סוג דם: {donor['blood_type']} | {status}")
        
        # Emergency system info
        self.stdout.write('\n🚨 מערכת חירום:')
        self.stdout.write('-' * 60)
        
        # Count available O- donors
        available_o_negative = 0
        for donor in Donor.objects.filter(blood_type='O-'):
            if donor.can_donate:
                available_o_negative += 1
        
        self.stdout.write(f"✅ מספר תורמי O- זמינים: {available_o_negative}")
        self.stdout.write(f"✅ יחידות דם זמינות בחירום: {available_o_negative}")
        self.stdout.write("💡 תורמי O- לא תרמו ב-56 הימים האחרונים - זמינים לתרומת חירום!")
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 מילוי הנתונים הסתיים בהצלחה!'))
        self.stdout.write('🚀 הפעל: python manage.py runserver')
        self.stdout.write('📱 תבדקו עם פרטי הכניסה שלמעלה')
        self.stdout.write('🚨 דף החירום אמור לעבוד עכשיו עם תורמי O- זמינים!')
        self.stdout.write('='*60)