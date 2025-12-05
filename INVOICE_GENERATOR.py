from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from tabulate import tabulate
from datetime import date
import webbrowser
import time
import mysql.connector
import matplotlib.pyplot as plt
from reportlab.lib import colors


class Generate_invoice:
    def __init__(self):
        # Connect to MySQL database
        self.conn = mysql.connector.connect(
            host="localhost", user="root", password="", database="grocery_shop"
        )
        self.cursor = self.conn.cursor()

    def calculate_totals(self, items):
        subtotal = float(sum(item_s["quantity"] * item_s["price"] for item_s in items))
        tax = subtotal * 0.05
        discount = subtotal * 0.02
        total = subtotal + tax - discount
        return subtotal, tax, discount, total

    def save_to_database(
        self,
        customer_name,
        customer_address,
        customer_number,
        items,
        subtotal,
        tax,
        discount,
        total
    ):
        # Convert items to a string for storage
        items_str = "\n".join(
            [f"{item['name']} - {item['quantity']} x {item['price']}" for item in items]
        )
        sql = "INSERT INTO invoice (customer_name, customer_address, customer_number, items, subtotal, tax, discount, TOTAL, ORDER_DATE) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (
            customer_name,
            customer_address,
            customer_number,
            items_str,
            subtotal,
            tax,
            discount,
            total,
            date.today(),
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid

    def generate_invoice(
        self, filename, customer_name, customer_address, items, customer_number
    ):
        shop_name = "SHAKIL’S GROCERY SHOP"
        shop_address = "Ahmedabad"
        shop_contact = "+91 9725845511"
        shop_email = "kandhalshakil@shakil.com"
        subtotal, tax, discount, total = self.calculate_totals(items)

        # Save invoice details to the database
        id = self.save_to_database(
            customer_name,
            customer_address,
            customer_number,
            items,
            subtotal,
            tax,
            discount,
            int(total),
        )

        # set the filename
        filename = str(id) + "_" + filename
        c = canvas.Canvas(filename, pagesize=letter)

        # Shop Info Header
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.darkblue)
        c.drawString(50, 750, shop_name)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        c.drawString(470, 750, date.today().strftime("%d/%m/%Y"))
        c.line(50, 740, 550, 740)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 725, "From: Kandhal Shakil")
        c.drawString(50, 710, f"Shop Address: {shop_address}")
        c.drawString(50, 695, f"Contact Number: {shop_contact}")
        c.drawString(50, 680, f"Shop Email: {shop_email}")

        # Customer Info Header
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        c.drawString(300, 725, f"Invoice to:{customer_name}")
        c.drawString(300, 710, f"Customer Address: {customer_address}")
        c.drawString(300, 695, f"Customer Contact: {customer_number}")
        c.drawString(300, 680, f"Bill Number: {id}")

        # Table Headers
        c.setStrokeColor(colors.darkblue)
        c.setLineWidth(2)
        c.line(50, 650, 550, 650)
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 630, "DESCRIPTION")
        c.drawString(300, 630, "QTY")
        c.drawString(350, 630, "PRICE")
        c.drawString(450, 630, "TOTAL")

        # Table Rows with Alternating Row Colors
        c.setFillColor(colors.black)
        y = 600
        alternate = True
        for item in items:
            if alternate:
                c.setFillColor(colors.lightskyblue)
                c.rect(48, y - 8, 500, 20, stroke=0, fill=1)
            c.setFillColor(colors.black)
            c.drawString(50, y, item["name"])
            c.drawString(302, y, str(item["quantity"]))
            c.drawString(352, y, f"{item['price']}")
            c.drawString(452, y, f"{item['quantity'] * item['price']}")
            y -= 25
            alternate = not alternate  # Change color

        c.setStrokeColor(colors.darkblue)
        c.setLineWidth(2)
        c.line(50, y - 10, 550, y - 10)
        y -= 30

        c.setFillColor(colors.lightgrey)
        c.rect(50, y - 100, 500, 100, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.drawString(50, y - 30, f"SUB-TOTAL: {subtotal}")
        c.drawString(50, y - 50, f"TAX [(CGST : 2.5%)+(SGST : 2.5%)]: {tax}")
        c.drawString(50, y - 70, f"DISCOUNT (2%): -{discount}")
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y - 90, f"TOTAL: {round(total, 0)}")

        # Footer Section
        y -= 120
        c.setFillColor(colors.aqua)
        c.rect(40, y - 40, 520, 30, stroke=0, fill=1)
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.black)
        c.drawString(50, y - 30, "● Thank You For Buying From Shakil Grocery Shop! ●")

        for i in items:
            id = self.id_by_name(item["name"])[0]
            stock = self.id_by_name(item["name"])[3]
            if id:
                self.cursor.execute(
                    f"UPDATE items SET stock = {stock - item['quantity']} WHERE item_id = {id}"
                )
                self.conn.commit()

        c.save()
        return filename

    def view_items(self):
        self.cursor.execute("SELECT * FROM items")
        items = self.cursor.fetchall()
        headers = ["ID", "Name", "Price", "Stock"]
        data = [(item[0], item[1], item[2], item[3]) for item in items]
        table = tabulate(data, headers=headers, tablefmt="fancy_grid")
        print(table)

    def id_by_name(self, name):
        self.cursor.execute(f"SELECT * FROM items WHERE ITEM_NAME = '{name}'")
        item = self.cursor.fetchone()
        if item:
            return item
        else:
            return None

    def add_items(self):
        item_name = input("Enter item name: ")
        item_price = float(input("Enter item price: "))
        item_stock = int(input("Enter item stock: "))
        sql = "INSERT INTO items(ITEM_NAME, ITEM_PRICE, stock) VALUES (%s, %s, %s)"
        values = (item_name, item_price, item_stock)
        generate_invoice.cursor.execute(sql, values)
        generate_invoice.conn.commit()
        print("Item added successfully.")

    def generate_invoice_start(self):
        customer_name = input("Enter customer name: ")
        customer_address = input("Enter customer address: ")
        customer_number = input("Enter customer mobile number: ")
        items_list = []
        while True:
            add = True
            print("\nAvailable items:")
            generate_invoice.view_items()
            item_id = int(input("\nEnter item ID (0 to exit): "))
            if item_id == 0:
                break
            self.cursor.execute(f"SELECT * FROM items where ITEM_ID = {item_id}")
            items = self.cursor.fetchall()
            headers = ["ID", "Name", "Price", "Stock"]
            data = [(item[0], item[1], item[2], item[3]) for item in items]
            table = tabulate(data, headers=headers, tablefmt="fancy_grid")
            print(table)
            add = input("Do you want to Add this item ? (y/n) : ")
            if add.lower() == "n":
                continue
            elif add.lower() == "y":
                item_quantity = int(input("Enter item quantity: "))
                item = self.get_item_by_id(item_id)
                for i in items_list:
                    if i["name"] == item[1]:
                        if item[3] - i["quantity"] < item_quantity:
                            print(f"Item '{item[1]}' is out of stock.")
                            continue
                        i["quantity"] += item_quantity
                        add = False
                        break
                if item:
                    if item[3] - item_quantity < item_quantity:
                        print(f"Item '{item[1]}' is out of stock.")
                        continue
                    if add:
                        items_list.append(
                            {
                                "name": item[1],
                                "quantity": item_quantity,
                                "price": item[2],
                            }
                        )
                else:
                    print("Item not found.")
        if len(items_list) > 0:
            return generate_invoice.generate_invoice(
                f"{customer_name}_{date.today().strftime('%d%m%Y')}.pdf",
                customer_name,
                customer_address,
                items_list,
                customer_number,
            )
        else:
            print("No items Add in The Card.")
            return None

    def get_item_by_id(self, item_id):
        self.cursor.execute(f"SELECT * FROM items WHERE ITEM_ID={item_id}")
        return self.cursor.fetchone()

    def update_item_stock(self, item_id, stock):
        sql = "UPDATE items SET STOCK=%s WHERE ITEM_ID=%s"
        values = (stock, item_id)
        self.cursor.execute(sql, values)
        self.conn.commit()

    def display_sales_graph(self):
        self.cursor.execute(
            "SELECT ORDER_DATE, SUM(TOTAL) FROM invoice GROUP BY ORDER_DATE"
        )
        sales_data = self.cursor.fetchall()

        if not sales_data:
            print("No sales data available to display.")
            return

        dates = [row[0] for row in sales_data]
        totals = [row[1] for row in sales_data]

        plt.figure(figsize=(10, 6))
        plt.plot(
            dates, totals, marker="o", linestyle="-", color="blue", label="Daily Sales"
        )

        plt.title("Daily Sales Report", fontsize=16)
        plt.xlabel("Date", fontsize=14)
        plt.ylabel("Total Sales (in ₹)", fontsize=14)
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.xticks(rotation=45, fontsize=10)
        plt.yticks(fontsize=10)
        plt.legend(fontsize=12)

        plt.tight_layout()
        plt.show()

    def display_sales_report(self):
        self.cursor.execute("SELECT * FROM invoice")
        headers = [
            "ID",
            "Customer Name",
            "Customer Address",
            "Invoice Date",
            "Total Amount",
        ]
        data = [
            (row[0], row[1], row[2], row[9].strftime("%d-%m-%Y"), row[8])
            for row in self.cursor.fetchall()
        ]
        table = tabulate(data, headers=headers, tablefmt="fancy_grid")
        print("\n")
        for row in table:
            print(row, end="")
            time.sleep(0.0005)

        print("\n")
        print("Sales Report Displayed Successfully.")
        print("\n")
        generate_invoice.cursor.execute(
            "SELECT ORDER_DATE , SUM(TOTAL) FROM invoice GROUP BY ORDER_DATE"
        )
        sales_data = generate_invoice.cursor.fetchall()
        headers = ["DATE", "SALES"]
        data = [(row[0], row[1]) for row in sales_data]
        table = tabulate(data, headers=headers, tablefmt="fancy_grid")
        print("\n")
        for row in table:
            print(row, end="")
            time.sleep(0.0005)
        print("\n")
        print("Sales Report Displayed Successfully.")
        print("\n")

        generate_invoice.cursor.execute("SELECT SUM(TOTAL) FROM invoice")
        total_sales = int(generate_invoice.cursor.fetchone()[0])
        print(f"Total Sales: {total_sales}")

    def find_invoice_by_bill_number(self):
        bill_number = input("Enter the Bill Number to search for: ")
        try:
            self.cursor.execute(
                "SELECT * FROM invoice WHERE INVOICE_ID = %s", (bill_number,)
            )
            invoice = self.cursor.fetchone()
            if invoice:
                headers = [
                    "Bill Number",
                    "Customer Name",
                    "Customer Address",
                    "Customer Contact",
                    "Sub Total",
                    "Tax",
                    "Discount",
                    "Total",
                    "Order Date",
                ]
                data = [
                    (
                        invoice[0],
                        invoice[1],
                        invoice[2],
                        invoice[3],
                        invoice[5],
                        invoice[6],
                        invoice[7],
                        invoice[8],
                        invoice[9].strftime("%d-%m-%Y"),
                    )
                ]
                table = tabulate(data, headers=headers, tablefmt="fancy_grid")
                print("\nInvoice Details:")
                print(table)
                print("Item Details:")
                headers = ["Item Name", "Item Price", "Quantity", "Amount"]
                it = invoice[4].split("\n")
                data = []
                for i in it:
                    item_name = i.split("-")[0]
                    item_price = float(i.split("-")[1].split("x")[1])
                    quantity = float(i.split("-")[1].split("x")[0])
                    amount = item_price * quantity
                    data.append((item_name, item_price, quantity, amount))

                table = tabulate(data, headers=headers, tablefmt="fancy_grid")
                print(table)
            else:
                print("No invoice found with the given Bill Number.")
        except Exception as e:
            print(f"An error occurred while fetching the invoice: {e}")

        print("\n")


    def find_invoice(self):
        try:
            self.cursor.execute("SELECT * FROM invoice")
            invoices = self.cursor.fetchall()
            for invoice in invoices:
                headers = [
                    "Bill Number",
                    "Customer Name",
                    "Customer Address",
                    "Customer Contact",
                    "Sub Total",
                    "Tax",
                    "Discount",
                    "Total",
                    "Order Date",
                ]
                data = [
                    (

                        invoice[0],
                        invoice[1],
                        invoice[2],
                        invoice[3],
                        invoice[5],
                        invoice[6],
                        invoice[7],
                        invoice[8],
                        invoice[9].strftime("%d-%m-%Y"),
                    )
                ]
                table = tabulate(data, headers=headers, tablefmt="fancy_grid")
                print("\nInvoice Details:")
                print(table)

        except Exception as e:
            print(f"An error occurred while fetching the invoice: {e}")

        print("\n")

    def search_item(self):
        item_name = input("Enter item name to search for: ")
        self.cursor.execute(
            "SELECT * FROM items WHERE LOWER(ITEM_NAME) LIKE %s",
            ("%" + item_name.lower() + "%",),
        )
        items = self.cursor.fetchall()
        if items:
            headers = ["ID", "Name", "Price", "Stock"]
            data = [(row[0], row[1], row[2], row[3]) for row in items]
            table = tabulate(data, headers=headers, tablefmt="fancy_grid")
            print("\n")
            for row in table:
                print(row, end="")
                time.sleep(0.0005)
        else:
            print("No items found with the given name.")

    def exit_program(self):
        print("Thank you for using Shakil Grocery Shop! Goodbye.")
        exit()

    def run(self):
        while True:
            try:
                b = self.run_menu()
                print("\n")
                if b == True:
                    raise ValueError
            except ValueError:
                print("Error : Invalid input. Please try again.")
                continue

    def run_menu(self):
        print("1. Add Item")
        print("2. View Items")
        print("3. Update")
        print("4. Remove Item")
        print("5. Generate Invoice")
        print("6. Display Sales Graph")
        print("7. Display Sales Report")
        print("8. Find Invoice Details using Bill Number")
        print("9. Search item")
        print("10. Show All invoices")
        print("11. Exit")
        choice = int(input("Enter your choice: "))
        if choice == 1:
            generate_invoice.add_items()
            print("\nItem added successfully.")
        elif choice == 2:
            print()
            generate_invoice.view_items()
            print("\n")
        elif choice == 3:
            generate_invoice.view_items()
            item_id = int(input("Enter item ID to update stock or price: "))
            item = generate_invoice.cursor.execute(
                f"SELECT item_id FROM  items WHERE item_id={item_id}"
            )
            item = generate_invoice.cursor.fetchone()
            if item:
                type = int(
                    input("1. update price \n2. Update Stock\nEnter Your Choice : ")
                )
                if type == 1:
                    new_price = float(input("Enter new price: "))
                    generate_invoice.cursor.execute(
                        f"UPDATE items SET ITEM_PRICE={new_price} WHERE item_id={item_id}"
                    )
                    generate_invoice.conn.commit()
                    print("Item price updated successfully.")
                elif type == 2:
                    new_stock = int(input("Enter new stock: "))
                    generate_invoice.cursor.execute(
                        f"UPDATE items SET STOCK= STOCK + {new_stock} WHERE item_id={item_id}"
                    )
                    generate_invoice.conn.commit()
                    print("Item stock updated successfully.")
            else:
                print("Item not found.")
            print("\n")
        elif choice == 4:
            generate_invoice.view_items()
            item_id = int(input("Enter item ID to remove: "))
            item = generate_invoice.cursor.execute(
                f"SELECT item_id FROM  items WHERE item_id={item_id}"
            )
            item = generate_invoice.cursor.fetchone()
            if item:
                generate_invoice.cursor.execute(
                    f"DELETE FROM items WHERE item_id={item_id}"
                )
                generate_invoice.conn.commit()
                print("Item removed successfully.")
            else:
                print("Item not found.")
            print("\n")

        elif choice == 5:
            file = generate_invoice.generate_invoice_start()
            if file and (input("Do You Want to Open Invoice? (Y/N): ")).upper() == "Y":
                webbrowser.open(file)
        elif choice == 6:
            generate_invoice.display_sales_graph()
        elif choice == 7:
            generate_invoice.display_sales_report()
        elif choice == 8:
            generate_invoice.find_invoice_by_bill_number()
        elif choice == 9:
            generate_invoice.search_item()
        elif choice == 10:
            generate_invoice.find_invoice()
        elif choice == 11:
            generate_invoice.exit_program()
        else:
            return True


generate_invoice = Generate_invoice()
print("Welcome to Shakil Grocery Shop! \n")
try:
    generate_invoice.run()
    print("Thank you for using Shakil Grocery Shop! Goodbye.")
    generate_invoice.cursor.close()
    generate_invoice.conn.close()
except Exception as e:
    print(f'Error : {e}')
