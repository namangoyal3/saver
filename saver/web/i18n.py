"""
Simple translation system for the Saver web app.
Supports English (en) and Indonesian (id).
"""

TRANSLATIONS = {
    "en": {
        # Nav
        "nav_dashboard": "Dashboard",
        "nav_chat": "Chat",
        "nav_goals": "Goals",
        "nav_logout": "Logout",
        "nav_language": "Language",

        # Dashboard
        "dash_hello": "Hello, {name}!",
        "dash_snapshot": "Your financial snapshot",
        "dash_today_target": "Today's Target",
        "dash_more_to_go": "{amount} more to go",
        "dash_target_reached": "Target reached!",
        "dash_weekly_progress": "Weekly Progress",
        "dash_days_left": "{n} days left this week",
        "dash_efficiency": "Your Efficiency",
        "dash_per_hour": "/hr",
        "dash_profit_trip": "profit/trip",
        "dash_vs_last_week": "vs last week",
        "dash_upcoming_bills": "Upcoming Bills",
        "dash_today": "today",
        "dash_tomorrow": "tomorrow",
        "dash_in_days": "in {n}d",
        "dash_shortfall": "Shortfall of {amount} — earn extra or reduce spending",
        "dash_savings_rules": "Smart Auto-Save Rules",
        "dash_projected": "Projected savings: {monthly}/month ({yearly}/year)",
        "dash_tips": "Money-Saving Tips",
        "dash_saver_says": "Saver Says",
        "dash_insights": "Personalized insights",
        "dash_analyzing": "Analyzing your finances...",
        "dash_monthly_income": "Monthly Income",
        "dash_weekly_spending": "This Week's Spending",
        "dash_grab_net": "Grab Net (30d)",
        "dash_trips_week": "Trips This Week",
        "dash_week_avg": "/week avg",
        "dash_categories": "categories",
        "dash_fees": "Fees",
        "dash_expense_breakdown": "Expense Breakdown (7 days)",
        "dash_forecast": "14-Day Cashflow Forecast",
        "dash_min_balance": "Expected min balance",
        "dash_neg_risk": "Negative balance risk",
        "dash_high_risk": "High-risk dates",
        "dash_goals": "Your Goals",
        "dash_manage_goals": "Manage goals",
        "dash_complete": "complete",
        "dash_deeper": "Want deeper analysis?",
        "dash_deeper_sub": "Chat with Saver for detailed advice on your spending, savings, and goals",
        "dash_chat_saver": "Chat with Saver",

        # Chat
        "chat_welcome": "Hi {name}! I'm Saver, your financial wellness coach.",
        "chat_try": "Try one of these:",
        "chat_placeholder": "Ask about your finances...",
        "chat_trace": "Toggle trace",
        "chat_error": "Sorry, something went wrong. Please try again.",
        "chip_where_money": "Where did my money go?",
        "chip_earnings": "How much did I earn?",
        "chip_forecast": "Cashflow forecast",
        "chip_save": "Can I save {amount}?",
        "chip_grow": "How to grow my money?",

        # Goals
        "goals_title": "Savings Goals",
        "goals_create": "Create a New Goal",
        "goals_name": "Goal Name",
        "goals_target": "Target Amount",
        "goals_date": "Target Date (optional)",
        "goals_create_btn": "Create Goal",
        "goals_simulate": "Simulate a Goal",
        "goals_simulate_desc": "Check if a savings goal is feasible based on your earnings history.",
        "goals_months": "Months",
        "goals_simulate_btn": "Simulate",
        "goals_none": "No goals yet",
        "goals_none_sub": "Create your first savings goal above!",
        "goals_saved": "saved of",
        "goals_due": "Due",
        "goals_feasible": "Feasible!",
        "goals_stretch": "Stretch goal",
        "goals_suggested": "Suggested weekly",
        "goals_risk_weeks": "Risk weeks",

        # Login
        "login_title": "Your financial wellness coach",
        "login_subtitle": "For Grab driver-partners & delivery-partners",
        "login_select": "Select your profile",
        "login_disclaimer": "Demo with synthetic data \u00b7 Not licensed financial advice",

        # Disclaimer
        "disclaimer": "Saver provides financial education and budgeting tools only \u2014 not licensed financial advice.",
    },

    "id": {
        # Nav
        "nav_dashboard": "Dasbor",
        "nav_chat": "Obrolan",
        "nav_goals": "Target",
        "nav_logout": "Keluar",
        "nav_language": "Bahasa",

        # Dashboard
        "dash_hello": "Halo, {name}!",
        "dash_snapshot": "Ringkasan keuangan Anda",
        "dash_today_target": "Target Hari Ini",
        "dash_more_to_go": "{amount} lagi",
        "dash_target_reached": "Target tercapai!",
        "dash_weekly_progress": "Kemajuan Mingguan",
        "dash_days_left": "{n} hari lagi minggu ini",
        "dash_efficiency": "Efisiensi Anda",
        "dash_per_hour": "/jam",
        "dash_profit_trip": "untung/perjalanan",
        "dash_vs_last_week": "vs minggu lalu",
        "dash_upcoming_bills": "Tagihan Mendatang",
        "dash_today": "hari ini",
        "dash_tomorrow": "besok",
        "dash_in_days": "dalam {n}h",
        "dash_shortfall": "Kekurangan {amount} \u2014 cari tambahan atau kurangi pengeluaran",
        "dash_savings_rules": "Aturan Tabungan Otomatis",
        "dash_projected": "Proyeksi tabungan: {monthly}/bulan ({yearly}/tahun)",
        "dash_tips": "Tips Hemat Uang",
        "dash_saver_says": "Kata Saver",
        "dash_insights": "Wawasan pribadi",
        "dash_analyzing": "Menganalisis keuangan Anda...",
        "dash_monthly_income": "Pendapatan Bulanan",
        "dash_weekly_spending": "Pengeluaran Minggu Ini",
        "dash_grab_net": "Grab Bersih (30h)",
        "dash_trips_week": "Perjalanan Minggu Ini",
        "dash_week_avg": "/minggu rata-rata",
        "dash_categories": "kategori",
        "dash_fees": "Biaya",
        "dash_expense_breakdown": "Rincian Pengeluaran (7 hari)",
        "dash_forecast": "Prakiraan Arus Kas 14 Hari",
        "dash_min_balance": "Saldo minimum yang diharapkan",
        "dash_neg_risk": "Risiko saldo negatif",
        "dash_high_risk": "Tanggal berisiko tinggi",
        "dash_goals": "Target Anda",
        "dash_manage_goals": "Kelola target",
        "dash_complete": "selesai",
        "dash_deeper": "Ingin analisis lebih dalam?",
        "dash_deeper_sub": "Obrolan dengan Saver untuk saran detail tentang pengeluaran, tabungan, dan target Anda",
        "dash_chat_saver": "Obrolan dengan Saver",

        # Chat
        "chat_welcome": "Hai {name}! Saya Saver, pelatih kesehatan keuangan Anda.",
        "chat_try": "Coba salah satu ini:",
        "chat_placeholder": "Tanya tentang keuangan Anda...",
        "chat_trace": "Tampilkan jejak",
        "chat_error": "Maaf, terjadi kesalahan. Silakan coba lagi.",
        "chip_where_money": "Ke mana uang saya?",
        "chip_earnings": "Berapa pendapatan saya?",
        "chip_forecast": "Prakiraan arus kas",
        "chip_save": "Bisakah saya menabung {amount}?",
        "chip_grow": "Bagaimana cara mengembangkan uang saya?",

        # Goals
        "goals_title": "Target Tabungan",
        "goals_create": "Buat Target Baru",
        "goals_name": "Nama Target",
        "goals_target": "Jumlah Target",
        "goals_date": "Tanggal Target (opsional)",
        "goals_create_btn": "Buat Target",
        "goals_simulate": "Simulasi Target",
        "goals_simulate_desc": "Periksa apakah target tabungan layak berdasarkan riwayat pendapatan Anda.",
        "goals_months": "Bulan",
        "goals_simulate_btn": "Simulasi",
        "goals_none": "Belum ada target",
        "goals_none_sub": "Buat target tabungan pertama di atas!",
        "goals_saved": "tersimpan dari",
        "goals_due": "Tenggat",
        "goals_feasible": "Layak!",
        "goals_stretch": "Target ambisius",
        "goals_suggested": "Saran mingguan",
        "goals_risk_weeks": "Minggu berisiko",

        # Login
        "login_title": "Pelatih kesehatan keuangan Anda",
        "login_subtitle": "Untuk mitra pengemudi & pengantar Grab",
        "login_select": "Pilih profil Anda",
        "login_disclaimer": "Demo dengan data sintetis \u00b7 Bukan nasihat keuangan berlisensi",

        # Disclaimer
        "disclaimer": "Saver menyediakan edukasi keuangan dan alat anggaran saja \u2014 bukan nasihat keuangan berlisensi.",
    },
}


def t(key: str, lang: str = "en") -> str:
    """Return the translated string for *key* in the given language.

    Falls back to English if the key is missing in the requested language,
    and returns the key itself if it is not found in any language.
    """
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return translations.get(key, TRANSLATIONS["en"].get(key, key))


def get_translations(lang: str = "en") -> dict[str, str]:
    """Return the full translation dict for *lang* (for passing into templates).

    Falls back to English for any language that is not defined.
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"])
