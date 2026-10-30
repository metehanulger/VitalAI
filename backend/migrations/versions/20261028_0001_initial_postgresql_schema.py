"""Initial PostgreSQL schema and disease-to-clinic reference data.

Revision ID: 0001
Revises:
Create Date: 2026-10-28 14:39:01.955666
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REFERANS_SEVK_VERISI = [
    {
        'hastalik_adi': 'Acute myocardial infarction',
        'icd10_kodu': 'I21.9',
        'semptomlar': 'Crushing chest pain radiating to the left arm, cold sweating, tachycardia, dyspnea, elevated troponin',
        'birincil_poliklinik': 'Cardiology',
        'ikincil_poliklinik': 'Emergency Medicine',
        'varsayilan_triaj_kodu': 'KIRMIZI',
        'aciklama': 'Urgent angiography and cardiac intensive care are required.',
    },
    {
        'hastalik_adi': 'Acute ischemic stroke',
        'icd10_kodu': 'I63.9',
        'semptomlar': 'Sudden facial asymmetry, arm weakness, speech difficulty (aphasia), confusion',
        'birincil_poliklinik': 'Neurology',
        'ikincil_poliklinik': 'Interventional Radiology',
        'varsayilan_triaj_kodu': 'KIRMIZI',
        'aciklama': 'Thrombolytic treatment within the first 4.5 hours is critical.',
    },
    {
        'hastalik_adi': 'Acute pulmonary embolism',
        'icd10_kodu': 'I26.9',
        'semptomlar': 'Sudden sharp chest pain, marked tachypnea, hemoptysis, low SpO2',
        'birincil_poliklinik': 'Pulmonology',
        'ikincil_poliklinik': 'Cardiology',
        'varsayilan_triaj_kodu': 'KIRMIZI',
        'aciklama': 'Urgent CT angiography and oxygen support are required.',
    },
    {
        'hastalik_adi': 'Pneumothorax',
        'icd10_kodu': 'J93.9',
        'semptomlar': 'Severe one-sided chest pain while breathing, reduced breath sounds, cyanosis',
        'birincil_poliklinik': 'Thoracic Surgery',
        'ikincil_poliklinik': 'Emergency Medicine',
        'varsayilan_triaj_kodu': 'KIRMIZI',
        'aciklama': 'There is a risk of tension pneumothorax; urgent decompression is required.',
    },
    {
        'hastalik_adi': 'Acute appendicitis',
        'icd10_kodu': 'K35.8',
        'semptomlar': 'Pain starting around the navel and moving to the right lower abdomen, nausea, vomiting, leukocytosis',
        'birincil_poliklinik': 'General Surgery',
        'ikincil_poliklinik': 'Gastroenterology',
        'varsayilan_triaj_kodu': 'SARI',
        'aciklama': 'Surgery may be required; urgent ultrasound or CT is recommended.',
    },
    {
        'hastalik_adi': 'Acute cholecystitis',
        'icd10_kodu': 'K81.0',
        'semptomlar': 'Severe cramping pain in the right upper abdomen radiating to the back, worsening after meals, fever',
        'birincil_poliklinik': 'General Surgery',
        'ikincil_poliklinik': 'Gastroenterology',
        'varsayilan_triaj_kodu': 'SARI',
        'aciklama': 'Assess for biliary colic and risk of perforation.',
    },
    {
        'hastalik_adi': 'Urinary stone / renal colic',
        'icd10_kodu': 'N20.1',
        'semptomlar': 'Severe flank pain radiating to the groin, hematuria (blood in urine)',
        'birincil_poliklinik': 'Urology',
        'ikincil_poliklinik': 'Internal Medicine',
        'varsayilan_triaj_kodu': 'SARI',
        'aciklama': 'Urgent analgesia and urinary tract imaging are required.',
    },
    {
        'hastalik_adi': 'Pneumonia',
        'icd10_kodu': 'J18.9',
        'semptomlar': 'High fever, productive cough with dark sputum, side pain, crackles on auscultation',
        'birincil_poliklinik': 'Pulmonology',
        'ikincil_poliklinik': 'Infectious Diseases',
        'varsayilan_triaj_kodu': 'SARI',
        'aciklama': 'Antibiotic treatment and a chest X-ray are required.',
    },
    {
        'hastalik_adi': 'Diabetic ketoacidosis',
        'icd10_kodu': 'E10.1',
        'semptomlar': 'Excessive thirst, polyuria, fruity-smelling breath, abdominal pain, blood glucose above 300 mg/dL',
        'birincil_poliklinik': 'Endocrinology',
        'ikincil_poliklinik': 'Internal Medicine',
        'varsayilan_triaj_kodu': 'KIRMIZI',
        'aciklama': 'Begin the emergency IV insulin and hydration protocol.',
    },
    {
        'hastalik_adi': 'Hypertensive crisis',
        'icd10_kodu': 'I10',
        'semptomlar': 'Blood pressure above 180/120 mmHg, severe headache, blurred vision, nosebleed',
        'birincil_poliklinik': 'Cardiology',
        'ikincil_poliklinik': 'Internal Medicine',
        'varsayilan_triaj_kodu': 'SARI',
        'aciklama': 'Assess for end-organ damage involving the heart, brain, or kidneys.',
    },
    {
        'hastalik_adi': 'Open fracture / joint dislocation',
        'icd10_kodu': 'T14.2',
        'semptomlar': 'Abnormal limb movement, open wound, bone fragment, severe pain, deformity',
        'birincil_poliklinik': 'Orthopedics and Traumatology',
        'ikincil_poliklinik': 'Emergency Medicine',
        'varsayilan_triaj_kodu': 'SARI',
        'aciklama': 'Urgent reduction, splinting, and infection prophylaxis may be required.',
    },
    {
        'hastalik_adi': 'Acute meningitis',
        'icd10_kodu': 'G03.9',
        'semptomlar': 'Neck stiffness, high fever, photophobia, petechial rash',
        'birincil_poliklinik': 'Infectious Diseases',
        'ikincil_poliklinik': 'Neurology',
        'varsayilan_triaj_kodu': 'KIRMIZI',
        'aciklama': 'Urgent lumbar puncture and empiric antibiotics are required.',
    },
    {
        'hastalik_adi': 'Gastrointestinal bleeding',
        'icd10_kodu': 'K92.2',
        'semptomlar': 'Melena (black tarry stool), hematemesis (coffee-ground vomit), dizziness, anemia',
        'birincil_poliklinik': 'Gastroenterology',
        'ikincil_poliklinik': 'General Surgery',
        'varsayilan_triaj_kodu': 'KIRMIZI',
        'aciklama': 'Prepare for urgent endoscopy and blood transfusion.',
    },
    {
        'hastalik_adi': 'Acute sinusitis / upper respiratory infection',
        'icd10_kodu': 'J01.9',
        'semptomlar': 'Facial pressure, nasal congestion, mild headache, throat irritation',
        'birincil_poliklinik': 'Otolaryngology',
        'ikincil_poliklinik': 'Internal Medicine',
        'varsayilan_triaj_kodu': 'YESIL',
        'aciklama': 'Outpatient medical treatment and rest are sufficient.',
    },
    {
        'hastalik_adi': 'Minor soft-tissue injury',
        'icd10_kodu': 'T14.0',
        'semptomlar': 'Mild sprain, localized swelling, minimal pain with movement, normal circulation and sensation',
        'birincil_poliklinik': 'Orthopedics and Traumatology',
        'ikincil_poliklinik': 'Emergency Medicine',
        'varsayilan_triaj_kodu': 'YESIL',
        'aciklama': 'Cold application, elevation, and a simple analgesic are sufficient.',
    },
]


def upgrade() -> None:
    op.create_table('anlik_vitaller',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('nabiz', sa.SmallInteger(), nullable=False),
    sa.Column('tansiyon_sistolik', sa.SmallInteger(), nullable=False),
    sa.Column('tansiyon_diyastolik', sa.SmallInteger(), nullable=False),
    sa.Column('solunum', sa.SmallInteger(), nullable=False),
    sa.Column('ates', sa.Numeric(precision=4, scale=1, asdecimal=False), nullable=False),
    sa.Column('spo2', sa.SmallInteger(), nullable=False),
    sa.Column('troponin', sa.Numeric(precision=6, scale=3, asdecimal=False), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('ates BETWEEN 25 AND 45', name='ck_vit_ates'),
    sa.CheckConstraint('nabiz BETWEEN 20 AND 300', name='ck_vit_nabiz'),
    sa.CheckConstraint('solunum BETWEEN 4 AND 80', name='ck_vit_solunum'),
    sa.CheckConstraint('spo2 BETWEEN 30 AND 100', name='ck_vit_spo2'),
    sa.CheckConstraint('tansiyon_diyastolik BETWEEN 20 AND 200', name='ck_vit_diyastolik'),
    sa.CheckConstraint('tansiyon_sistolik BETWEEN 40 AND 300', name='ck_vit_sistolik'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('hasta_demografi',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('isim', sa.String(length=400), nullable=False),
    sa.Column('yas', sa.SmallInteger(), nullable=False),
    sa.Column('boy', sa.SmallInteger(), nullable=True),
    sa.Column('kilo', sa.Numeric(precision=5, scale=1, asdecimal=False), nullable=True),
    sa.Column('kan_grubu', sa.String(length=10), nullable=False),
    sa.Column('kimlik_turu', sa.String(length=10), nullable=False),
    sa.Column('kimlik_no', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('boy IS NULL OR boy BETWEEN 20 AND 260', name='ck_demo_boy'),
    sa.CheckConstraint('kilo IS NULL OR kilo BETWEEN 0.5 AND 400', name='ck_demo_kilo'),
    sa.CheckConstraint('yas BETWEEN 0 AND 130', name='ck_demo_yas'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_demografi_kimlik', 'hasta_demografi', ['kimlik_no'], unique=False)
    op.create_table('hasta_sikayet',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('ana_sikayet', sa.Text(), nullable=False),
    sa.Column('agri_skalasi', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('agri_skalasi BETWEEN 1 AND 10', name='ck_sikayet_agri'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('hastalik_sevk_referans',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('hastalik_adi', sa.String(length=200), nullable=False),
    sa.Column('icd10_kodu', sa.String(length=20), nullable=True),
    sa.Column('semptomlar', sa.String(length=2000), nullable=False),
    sa.Column('birincil_poliklinik', sa.String(length=100), nullable=False),
    sa.Column('ikincil_poliklinik', sa.String(length=100), nullable=True),
    sa.Column('varsayilan_triaj_kodu', sa.String(length=20), nullable=False),
    sa.Column('aciklama', sa.String(length=1000), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ml_birincil', 'hastalik_sevk_referans', ['birincil_poliklinik'], unique=False)
    op.create_index('ix_ml_hastalik', 'hastalik_sevk_referans', ['hastalik_adi'], unique=False)
    op.create_table('tibbi_gecmis',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('kronik_rahatsizlik', sa.String(length=2000), nullable=True),
    sa.Column('surekli_ilac', sa.String(length=2000), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('hastane_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('sira_no', sa.Integer(), nullable=False),
    sa.Column('tarih', sa.Date(), nullable=False),
    sa.Column('saat', sa.Time(), nullable=False),
    sa.Column('demografi_id', sa.Integer(), nullable=False),
    sa.Column('tibbi_gecmis_id', sa.Integer(), nullable=False),
    sa.Column('vitaller_id', sa.Integer(), nullable=False),
    sa.Column('sikayet_id', sa.Integer(), nullable=False),
    sa.Column('durum', sa.String(length=20), nullable=False),
    sa.Column('risk_skoru', sa.SmallInteger(), nullable=False),
    sa.Column('onerilen_poliklinik', sa.String(length=150), nullable=True),
    sa.Column('birim_uyumluluk_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('kritik_bulgu', sa.String(length=1500), nullable=True),
    sa.Column('erken_uyari_notu', sa.String(length=1500), nullable=True),
    sa.Column('aciklama', sa.String(length=2000), nullable=True),
    sa.Column('karar_kaynagi', sa.String(length=50), nullable=False),
    sa.Column('news2_skoru', sa.SmallInteger(), nullable=False),
    sa.Column('islendi', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("durum IN ('KIRMIZI', 'SARI', 'YESIL')", name='ck_log_durum'),
    sa.CheckConstraint('risk_skoru BETWEEN 1 AND 5', name='ck_log_risk'),
    sa.ForeignKeyConstraint(['demografi_id'], ['hasta_demografi.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sikayet_id'], ['hasta_sikayet.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tibbi_gecmis_id'], ['tibbi_gecmis.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['vitaller_id'], ['anlik_vitaller.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tarih', 'sira_no', name='uq_log_tarih_sira')
    )
    op.create_index('ix_log_gecmis', 'hastane_log', ['tarih', 'saat', 'sira_no'], unique=False)
    op.create_index('ix_log_kuyruk', 'hastane_log', ['tarih', 'risk_skoru', 'sira_no'], unique=False)

    referans = sa.table(
        'hastalik_sevk_referans',
        *(sa.column(name, sa.String) for name in REFERANS_SEVK_VERISI[0]),
    )
    op.bulk_insert(referans, REFERANS_SEVK_VERISI)


def downgrade() -> None:
    op.drop_index('ix_log_kuyruk', table_name='hastane_log')
    op.drop_index('ix_log_gecmis', table_name='hastane_log')
    op.drop_table('hastane_log')
    op.drop_table('tibbi_gecmis')
    op.drop_index('ix_ml_hastalik', table_name='hastalik_sevk_referans')
    op.drop_index('ix_ml_birincil', table_name='hastalik_sevk_referans')
    op.drop_table('hastalik_sevk_referans')
    op.drop_table('hasta_sikayet')
    op.drop_index('ix_demografi_kimlik', table_name='hasta_demografi')
    op.drop_table('hasta_demografi')
    op.drop_table('anlik_vitaller')
