"""Synthetic (fake but realistic) data pools for ATA form generation.

All names, companies, emails and IDs here are invented. None refer to real
people. International mix per requirements: EU + Turkey + others. Turkey / non-EU
placements are used to drive the "rejected: location not eligible" category.
"""

# (first, last) — deliberately international
NAMES = [
    ("Jakub", "Kowalski"), ("Anna", "Nowak"), ("Piotr", "Wisniewski"),
    ("Maria", "Wojcik"), ("Katarzyna", "Kaminska"), ("Tomasz", "Lewandowski"),
    ("Lukas", "Muller"), ("Sophie", "Schmidt"), ("Lena", "Fischer"),
    ("Matteo", "Rossi"), ("Giulia", "Ferrari"), ("Lucas", "Martin"),
    ("Emma", "Bernard"), ("Hugo", "Dubois"), ("Sofia", "Silva"),
    ("Joao", "Santos"), ("Elena", "Popescu"), ("Andrei", "Ionescu"),
    ("Nikola", "Horvat"), ("Ana", "Kovac"), ("Mehmet", "Yilmaz"),
    ("Zeynep", "Demir"), ("Emre", "Sahin"), ("Elif", "Celik"),
    ("Can", "Aydin"), ("Deniz", "Arslan"), ("Ivan", "Petrov"),
    ("Olga", "Volkova"), ("Priya", "Sharma"), ("Rohan", "Patel"),
    ("Wei", "Chen"), ("Yuki", "Tanaka"), ("Omar", "Hassan"),
    ("Fatima", "Ali"), ("Diego", "Garcia"), ("Carmen", "Lopez"),
    ("Karel", "Novak"), ("Eva", "Svobodova"), ("Bram", "de Vries"),
    ("Sanne", "Jansen"),
]

FIELDS = [
    "Computer Engineering", "Computer Science", "Software Engineering",
    "Information Technology", "Data Science", "Cybersecurity",
    "Artificial Intelligence", "Electronics Engineering",
]

# EU-based companies (eligible)
EU_COMPANIES = [
    ("Comarch S.A.", "Al. Jana Pawla II 39A, 31-864 Krakow, Poland",
     "Enterprise software and IT services"),
    ("Asseco Poland S.A.", "Olchowa 14, 35-322 Rzeszow, Poland",
     "Software development and system integration"),
    ("SAP Deutschland SE", "Hasso-Plattner-Ring 7, 69190 Walldorf, Germany",
     "Enterprise resource planning software"),
    ("Spotify AB", "Regeringsgatan 19, 111 53 Stockholm, Sweden",
     "Audio streaming platform engineering"),
    ("Adyen N.V.", "Simon Carmiggeltstraat 6-50, 1011 DJ Amsterdam, Netherlands",
     "Payment processing technology"),
    ("Nokia Solutions", "Karakaari 7, 02610 Espoo, Finland",
     "Telecommunications and network infrastructure"),
    ("Criteo S.A.", "32 Rue Blanche, 75009 Paris, France",
     "Advertising technology and machine learning"),
    ("Bolt Technology OU", "Vana-Louna 15, 10134 Tallinn, Estonia",
     "Mobility and ride-hailing platform"),
    ("STMicroelectronics", "Via C. Olivetti 2, 20864 Agrate Brianza, Italy",
     "Semiconductor design and manufacturing"),
    ("Allegro.eu", "Grunwaldzka 182, 60-166 Poznan, Poland",
     "E-commerce marketplace platform"),
]

# Non-EU companies (drives rejection: internship location not eligible)
NON_EU_COMPANIES = [
    ("Trendyol Group", "Maslak Mah., 34485 Istanbul, Turkey",
     "E-commerce and logistics technology"),
    ("Getir", "Besiktas, 34340 Istanbul, Turkey",
     "Rapid grocery delivery platform"),
    ("Peak Games", "Sisli, 34394 Istanbul, Turkey",
     "Mobile game development"),
    ("Aselsan A.S.", "Mehmet Akif Ersoy Mah., 06200 Ankara, Turkey",
     "Defense electronics systems"),
    ("Careem", "Dubai Internet City, Dubai, United Arab Emirates",
     "Super-app and mobility services"),
    ("Yandex LLC", "Lva Tolstogo 16, 119021 Moscow, Russia",
     "Search engine and cloud services"),
    ("Infosys Ltd", "Electronics City, Bangalore 560100, India",
     "IT consulting and outsourcing"),
    ("Mercado Libre", "Av. Caseros 3039, Buenos Aires, Argentina",
     "Latin American e-commerce platform"),
]

CYCLES = ["I", "II"]
SEMESTERS = ["4", "5", "6", "7"]

MANAGER_COMMENTS = [
    "The student works in our backend team and contributes to production services. "
    "The internship tasks align with the learning outcomes.",
    "The candidate is involved in the development and maintenance of the company web "
    "platform, working closely with the engineering team.",
    "The student participates in QA automation and CI pipeline maintenance. We confirm "
    "the placement and supervision.",
    "The applicant supports our data engineering team with ETL pipelines and reporting. "
    "Supervision is provided by the lead engineer.",
    "The student is engaged in mobile application development and testing under the "
    "guidance of the product team.",
]


def student_id(i: int) -> str:
    return f"{40000 + i * 7 % 9000 + 1000:05d}"


def email_for(first: str, last: str, domain: str = "gmail.com") -> str:
    return f"{first.lower()}.{last.lower().replace(' ', '')}@{domain}"
