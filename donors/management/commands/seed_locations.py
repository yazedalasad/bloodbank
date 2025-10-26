# donors/management/commands/seed_locations.py
from django.core.management.base import BaseCommand
from donors.models import Location

class Command(BaseCommand):
    help = 'Seeds Israeli cities and villages'

    def handle(self, *args, **options):
        ISRAELI_LOCATIONS = [
            # Tel Aviv District
            {'name_he': 'תל אביב', 'name_en': 'Tel Aviv', 'city_type': 'city', 'district': 'tel_aviv', 'latitude': 32.0853, 'longitude': 34.7818, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'רמת גן', 'name_en': 'Ramat Gan', 'city_type': 'city', 'district': 'tel_aviv', 'latitude': 32.0684, 'longitude': 34.8248, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'בני ברק', 'name_en': 'Bnei Brak', 'city_type': 'city', 'district': 'tel_aviv', 'latitude': 32.0807, 'longitude': 34.8338, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'חולון', 'name_en': 'Holon', 'city_type': 'city', 'district': 'tel_aviv', 'latitude': 32.0158, 'longitude': 34.7795, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'בת ים', 'name_en': 'Bat Yam', 'city_type': 'city', 'district': 'tel_aviv', 'latitude': 32.0238, 'longitude': 34.7519, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'גבעתיים', 'name_en': 'Givatayim', 'city_type': 'city', 'district': 'tel_aviv', 'latitude': 32.0722, 'longitude': 34.8088, 'has_hospital': False, 'has_blood_bank': False},
            
            # Jerusalem District
            {'name_he': 'ירושלים', 'name_en': 'Jerusalem', 'city_type': 'city', 'district': 'jerusalem', 'latitude': 31.7683, 'longitude': 35.2137, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'בית שמש', 'name_en': 'Beit Shemesh', 'city_type': 'city', 'district': 'jerusalem', 'latitude': 31.7470, 'longitude': 34.9882, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'מבשרת ציון', 'name_en': 'Mevaseret Zion', 'city_type': 'local_council', 'district': 'jerusalem', 'latitude': 31.8034, 'longitude': 35.1506, 'has_hospital': False, 'has_blood_bank': False},
            
            # Central District
            {'name_he': 'ראשון לציון', 'name_en': 'Rishon LeZion', 'city_type': 'city', 'district': 'center', 'latitude': 31.9730, 'longitude': 34.7925, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'פתח תקווה', 'name_en': 'Petah Tikva', 'city_type': 'city', 'district': 'center', 'latitude': 32.0871, 'longitude': 34.8875, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'נתניה', 'name_en': 'Netanya', 'city_type': 'city', 'district': 'center', 'latitude': 32.3320, 'longitude': 34.8593, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'אשדוד', 'name_en': 'Ashdod', 'city_type': 'city', 'district': 'center', 'latitude': 31.8044, 'longitude': 34.6553, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'רחובות', 'name_en': 'Rehovot', 'city_type': 'city', 'district': 'center', 'latitude': 31.8928, 'longitude': 34.8113, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'כפר סבא', 'name_en': 'Kfar Saba', 'city_type': 'city', 'district': 'center', 'latitude': 32.1715, 'longitude': 34.9084, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'הרצליה', 'name_en': 'Herzliya', 'city_type': 'city', 'district': 'center', 'latitude': 32.1624, 'longitude': 34.8447, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'רעננה', 'name_en': 'Ra\'anana', 'city_type': 'city', 'district': 'center', 'latitude': 32.1848, 'longitude': 34.8713, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'הוד השרון', 'name_en': 'Hod HaSharon', 'city_type': 'city', 'district': 'center', 'latitude': 32.1304, 'longitude': 34.8866, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'רמלה', 'name_en': 'Ramla', 'city_type': 'city', 'district': 'center', 'latitude': 31.9292, 'longitude': 34.8659, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'לוד', 'name_en': 'Lod', 'city_type': 'city', 'district': 'center', 'latitude': 31.9510, 'longitude': 34.8881, 'has_hospital': True, 'has_blood_bank': False},
            
            # Haifa District
            {'name_he': 'חיפה', 'name_en': 'Haifa', 'city_type': 'city', 'district': 'haifa', 'latitude': 32.7940, 'longitude': 34.9896, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'נשר', 'name_en': 'Nesher', 'city_type': 'city', 'district': 'haifa', 'latitude': 32.7652, 'longitude': 35.0446, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'קרית אתא', 'name_en': 'Kiryat Ata', 'city_type': 'city', 'district': 'haifa', 'latitude': 32.8064, 'longitude': 35.1085, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'קרית ביאליק', 'name_en': 'Kiryat Bialik', 'city_type': 'city', 'district': 'haifa', 'latitude': 32.8275, 'longitude': 35.0858, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'קרית ים', 'name_en': 'Kiryat Yam', 'city_type': 'city', 'district': 'haifa', 'latitude': 32.8493, 'longitude': 35.0689, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'קרית מוצקין', 'name_en': 'Kiryat Motzkin', 'city_type': 'city', 'district': 'haifa', 'latitude': 32.8370, 'longitude': 35.0775, 'has_hospital': False, 'has_blood_bank': False},
            
            # Northern District
            {'name_he': 'נהריה', 'name_en': 'Nahariya', 'city_type': 'city', 'district': 'north', 'latitude': 33.0085, 'longitude': 35.0981, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'עכו', 'name_en': 'Acre', 'city_type': 'city', 'district': 'north', 'latitude': 32.9273, 'longitude': 35.0825, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'קרית שמונה', 'name_en': 'Kiryat Shmona', 'city_type': 'city', 'district': 'north', 'latitude': 33.2079, 'longitude': 35.5702, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'צפת', 'name_en': 'Safed', 'city_type': 'city', 'district': 'north', 'latitude': 32.9646, 'longitude': 35.4960, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'טבריה', 'name_en': 'Tiberias', 'city_type': 'city', 'district': 'north', 'latitude': 32.7959, 'longitude': 35.5310, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'נצרת', 'name_en': 'Nazareth', 'city_type': 'city', 'district': 'north', 'latitude': 32.6996, 'longitude': 35.3035, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'עפולה', 'name_en': 'Afula', 'city_type': 'city', 'district': 'north', 'latitude': 32.6100, 'longitude': 35.2875, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'כרמיאל', 'name_en': 'Karmiel', 'city_type': 'city', 'district': 'north', 'latitude': 32.9141, 'longitude': 35.2924, 'has_hospital': False, 'has_blood_bank': False},
            
            # Southern District
            {'name_he': 'באר שבע', 'name_en': 'Beer Sheva', 'city_type': 'city', 'district': 'south', 'latitude': 31.2529, 'longitude': 34.7915, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'אשקלון', 'name_en': 'Ashkelon', 'city_type': 'city', 'district': 'south', 'latitude': 31.6688, 'longitude': 34.5743, 'has_hospital': True, 'has_blood_bank': True},
            {'name_he': 'שדרות', 'name_en': 'Sderot', 'city_type': 'city', 'district': 'south', 'latitude': 31.5257, 'longitude': 34.5969, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'אופקים', 'name_en': 'Ofakim', 'city_type': 'city', 'district': 'south', 'latitude': 31.3141, 'longitude': 34.6203, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'קרית גת', 'name_en': 'Kiryat Gat', 'city_type': 'city', 'district': 'south', 'latitude': 31.6099, 'longitude': 34.7642, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'דימונה', 'name_en': 'Dimona', 'city_type': 'city', 'district': 'south', 'latitude': 31.0694, 'longitude': 35.0333, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'ירוחם', 'name_en': 'Yeruham', 'city_type': 'local_council', 'district': 'south', 'latitude': 30.9878, 'longitude': 34.9297, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'מצפה רמון', 'name_en': 'Mitzpe Ramon', 'city_type': 'local_council', 'district': 'south', 'latitude': 30.6096, 'longitude': 34.8019, 'has_hospital': False, 'has_blood_bank': False},
            
            # Judea and Samaria
            {'name_he': 'אריאל', 'name_en': 'Ariel', 'city_type': 'city', 'district': 'judea_samaria', 'latitude': 32.1043, 'longitude': 35.1852, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'מעלה אדומים', 'name_en': 'Ma\'ale Adumim', 'city_type': 'city', 'district': 'judea_samaria', 'latitude': 31.7774, 'longitude': 35.2987, 'has_hospital': False, 'has_blood_bank': False},
            
            # Additional important locations
            {'name_he': 'מודיעין', 'name_en': 'Modi\'in', 'city_type': 'city', 'district': 'center', 'latitude': 31.8980, 'longitude': 35.0103, 'has_hospital': True, 'has_blood_bank': False},
            {'name_he': 'רהט', 'name_en': 'Rahat', 'city_type': 'city', 'district': 'south', 'latitude': 31.3924, 'longitude': 34.7543, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'טייבה', 'name_en': 'Tayibe', 'city_type': 'city', 'district': 'center', 'latitude': 32.2662, 'longitude': 35.0089, 'has_hospital': False, 'has_blood_bank': False},
            {'name_he': 'אום אל-פחם', 'name_en': 'Umm al-Fahm', 'city_type': 'city', 'district': 'haifa', 'latitude': 32.5195, 'longitude': 35.1536, 'has_hospital': False, 'has_blood_bank': False},
        ]

        created_count = 0
        updated_count = 0
        
        for loc_data in ISRAELI_LOCATIONS:
            obj, created = Location.objects.get_or_create(
                name_he=loc_data['name_he'],
                defaults=loc_data
            )
            if created:
                created_count += 1
            else:
                # Update existing record
                for key, value in loc_data.items():
                    setattr(obj, key, value)
                obj.save()
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Successfully seeded locations: {created_count} created, {updated_count} updated'
        ))
        