# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    'name': 'Hospital Management System for Gynecologist',
    'version': '1.0.6',
    'summary': 'Hospital Management System for Gynecologist',
    'description': """
                Hospital Management System for Gynecologist. HealthCare Gynec system for hospitals
                With this module you can manage :
                - Gynec Patients
                - Maintain Child Birth Register
                - Record Abdominal Vaginal and Rectal examinations
                - Manage and print the reports for Pelvic Sonogrpahy, Follical Sonography
                    and Obstetric Sonography
                - Manage the Appointments for Pregnancies and hospitalizations. 
                - Record Colposcopy Mamography and Pap test  acs hms almightycs

                Sistema de gestión hospitalaria para ginecólogo.
                 Con este módulo podrás gestionar:
                 - Pacientes Gynec
                 - Mantener el registro de nacimientos de niños
                 - Registro de exámenes abdominales vaginales y rectales.
                 - Gestione e imprima los informes para la Sonografía pélvica, Sonografía Follical
                     y sonografía obstétrica
                 - Gestionar las citas de embarazo y hospitalizaciones.
                 - Registro de colposcopia mamografía y prueba de Papanicolaou 

                Krankenhausmanagementsystem für Frauenarzt
                 Mit diesem Modul können Sie Folgendes verwalten:
                 - Gynec-Patienten
                 - Das Geburtsregister für Kinder pflegen
                 - Aufzeichnung von Abdominal-, Vaginal- und Rektaluntersuchungen
                 - Verwalten und drucken Sie die Berichte für Becken Sonogrpahy, Follical Sonography
                     und Geburtshilfe Sonographie
                 - Verwalten Sie die Termine für Schwangerschaften und Krankenhausaufenthalte.
                 - Aufzeichnung der Kolposkopie-Mammographie und des Pap-Tests

                Système de gestion hospitalière pour gynécologue
                 Avec ce module, vous pouvez gérer:
                 - Patients Gynec
                 - Tenir un registre des naissances
                 - Enregistrement des examens abdominaux, vaginaux et rectaux
                 - Gérer et imprimer les rapports sur Sonogrpahy pelvienne, sonographie follique
                     et sonographie obstétrique
                 - Gérer les rendez-vous pour les grossesses et les hospitalisations.
                 - Record Colposcopy Mammographie et test de Pap 

                نظام إدارة المستشفيات لأمراض النساء
                 باستخدام هذه الوحدة ، يمكنك إدارة:
                 - مرضى النساء
                 - الحفاظ على سجل ولادة الطفل
                 - سجل فحوصات البطن والمهبل والمستقيم
                 - إدارة وطباعة التقارير لبيلفيك Sonogrpahy ، التصوير بالموجات الصوتية
                     والتوليد بالموجات فوق الصوتية
                 - إدارة المواعيد للحمل والمستشفيات.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             

    """,
    'category': 'Medical',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    'depends': ['acs_hms_hospitalization'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',    
        'data/data.xml',
        'views/hms_gynec_view.xml',
        'views/hms_base_view.xml',
        'views/hms_appointment_view.xml',
        'views/hms_pregnancy.xml',
        'views/hms_sonography_view.xml',
        'views/hms_childbirth_view.xml',
        'report/report_sono_follical.xml',
        'report/report_birth_card.xml',
        'report/report_sono_pelvis.xml',
        'report/report_sono_obstetric.xml',
        'report/report_pregnancy.xml',
        'views/menu_item.xml',
    ],
    'images': [
        'static/description/hms_gynec_almightycs_cover.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'price': 151,
    'currency': 'EUR',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: