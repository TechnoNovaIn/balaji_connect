from django.core.management.base import BaseCommand
from accounts.models import Department, Employee
from posts.models import Post

class Command(BaseCommand):
    help = "Seeds initial company departments, administrator, sample employees, and welcome posts."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Balaji Transports departments...")
        depts_data = [
            ("Operations", "OPS", "Fleet dispatches, driver management, and route planning."),
            ("Logistics & Fleet", "LOG", "Vehicle maintenance, cargo tracking, and warehouse hubs."),
            ("Information Technology", "IT", "Systems, digital communications, and data infrastructure."),
            ("Human Resources", "HR", "Personnel, recruitment, driver welfare, and employee training."),
            ("Finance & Accounts", "FIN", "Billing, accounting, customer payments, and freight audits."),
        ]

        depts = {}
        for name, code, desc in depts_data:
            dept, created = Department.objects.get_or_create(code=code, defaults={'name': name, 'description': desc})
            depts[code] = dept

        self.stdout.write("Seeding Administrator account...")
        admin = Employee.objects.filter(employee_id="BT-0001").first()
        if not admin:
            admin = Employee.objects.create_superuser(
                employee_id="BT-0001",
                username="bt-0001",
                first_name='Balaji',
                last_name='Administrator',
                email='admin@balajitransports.internal',
                department=depts['IT'],
                designation='System Administrator',
                role=Employee.Role.ADMIN,
                password='AdminPassword123!'
            )
            self.stdout.write(self.style.SUCCESS("Created Admin: BT-0001 / AdminPassword123!"))
        else:
            self.stdout.write("Admin BT-0001 already exists.")

        self.stdout.write("Seeding sample employees...")
        employees_data = [
            ("BT-1001", "Ramesh", "Kumar", "OPS", "Senior Fleet Supervisor", "EmployeePassword123!"),
            ("BT-1002", "Pooja", "Patel", "LOG", "Warehouse Operations Lead", "EmployeePassword123!"),
            ("BT-1003", "Suresh", "Verma", "FIN", "Billing & Freight Auditor", "EmployeePassword123!"),
        ]

        created_employees = []
        for emp_id, fname, lname, dept_code, desig, pwd in employees_data:
            emp = Employee.objects.filter(employee_id=emp_id).first()
            if not emp:
                emp = Employee.objects.create_user(
                    employee_id=emp_id,
                    username=emp_id.lower(),
                    first_name=fname,
                    last_name=lname,
                    department=depts[dept_code],
                    designation=desig,
                    role=Employee.Role.EMPLOYEE,
                    password=pwd
                )
                self.stdout.write(self.style.SUCCESS(f"Created Employee: {emp_id} ({fname} {lname}) / {pwd}"))
            created_employees.append(emp)

        self.stdout.write("Seeding initial company posts...")
        if not Post.objects.filter(author=admin).exists():
            Post.objects.create(
                author=admin,
                content="Welcome to Balaji Connect! 🚛\n\nThis is our private company network for Balaji Transports employees. Use this platform to share operational updates, team photos, milestones, and daily transport achievements.\n\nPlease remember to keep all posts professional and confidential."
            )
            self.stdout.write(self.style.SUCCESS("Created welcome post from admin."))

        if created_employees and not Post.objects.filter(author=created_employees[0]).exists():
            Post.objects.create(
                author=created_employees[0],
                content="Operations Update: All South Corridor deliveries departed on schedule today with 100% on-time departure rate. Kudos to the driving crew! 🛣️"
            )
            self.stdout.write(self.style.SUCCESS("Created sample operational post."))

        self.stdout.write(self.style.SUCCESS("\nSeed data process finished successfully!"))
