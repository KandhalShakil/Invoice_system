from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from tabulate import tabulate
from datetime import datetime, date
import webbrowser
import time
import matplotlib.pyplot as plt
from reportlab.lib import colors
from pymongo import MongoClient
from bson.objectid import ObjectId
import os


class MongoDB_Invoice_Generator:
    def __init__(self):
        # Connect to MongoDB
        connection_string = "mongodb+srv://kandhalshakil_db_user:ZTYYDRunhuBTz8sn@cluster0.omdl2yo.mongodb.net/"
        self.client = MongoClient(connection_string)
        self.db = self.client.grocery_shop
        self.items_collection = self.db.items
        self.invoices_collection = self.db.invoices
        
        # Create indexes for better performance
        self.items_collection.create_index("item_name")
        self.invoices_collection.create_index("invoice_id")
        self.invoices_collection.create_index("customer_name")
        
        print("Connected to MongoDB successfully!")

    def add_items(self):
        """Add items to inventory"""
        print("\n--- ADD ITEMS ---")
        item_name = input("Enter item name: ")
        item_price = float(input("Enter item price: "))
        stock = int(input("Enter stock quantity: "))
        
        # Check if item already exists
        existing_item = self.items_collection.find_one({"item_name": item_name})
        if existing_item:
            # Update stock if item exists
            self.items_collection.update_one(
                {"item_name": item_name},
                {"$inc": {"stock": stock}}
            )
            print(f"Updated stock for {item_name}. New stock: {existing_item['stock'] + stock}")
        else:
            # Create new item
            item_doc = {
                "item_name": item_name,
                "item_price": item_price,
                "stock": stock,
                "created_at": datetime.now()
            }
            result = self.items_collection.insert_one(item_doc)
            print(f"Item {item_name} added with ID: {result.inserted_id}")

    def view_items(self):
        """Display all items in inventory"""
        items = list(self.items_collection.find())
        if not items:
            print("No items in inventory.")
            return
        
        table_data = []
        for item in items:
            table_data.append([
                str(item["_id"]),
                item["item_name"],
                f"${item['item_price']:.2f}",
                item["stock"]
            ])
        
        print(tabulate(table_data, headers=["ID", "Item Name", "Price", "Stock"], tablefmt="grid"))

    def search_item(self):
        """Search for items by name"""
        search_term = input("Enter item name to search: ")
        items = list(self.items_collection.find({"item_name": {"$regex": search_term, "$options": "i"}}))
        
        if not items:
            print("No items found.")
            return
        
        table_data = []
        for item in items:
            table_data.append([
                str(item["_id"]),
                item["item_name"],
                f"${item['item_price']:.2f}",
                item["stock"]
            ])
        
        print(tabulate(table_data, headers=["ID", "Item Name", "Price", "Stock"], tablefmt="grid"))

    def update_item(self):
        """Update item price or stock"""
        self.view_items()
        item_id = input("Enter item ID to update: ")
        
        try:
            item = self.items_collection.find_one({"_id": ObjectId(item_id)})
            if not item:
                print("Item not found.")
                return
            
            print("1. Update price")
            print("2. Update stock")
            choice = int(input("Enter your choice: "))
            
            if choice == 1:
                new_price = float(input("Enter new price: "))
                self.items_collection.update_one(
                    {"_id": ObjectId(item_id)},
                    {"$set": {"item_price": new_price}}
                )
                print("Item price updated successfully.")
            elif choice == 2:
                additional_stock = int(input("Enter additional stock: "))
                self.items_collection.update_one(
                    {"_id": ObjectId(item_id)},
                    {"$inc": {"stock": additional_stock}}
                )
                print("Item stock updated successfully.")
            
        except Exception as e:
            print(f"Error updating item: {e}")

    def remove_item(self):
        """Remove item from inventory"""
        self.view_items()
        item_id = input("Enter item ID to remove: ")
        
        try:
            result = self.items_collection.delete_one({"_id": ObjectId(item_id)})
            if result.deleted_count > 0:
                print("Item removed successfully.")
            else:
                print("Item not found.")
        except Exception as e:
            print(f"Error removing item: {e}")

    def calculate_totals(self, items):
        """Calculate invoice totals"""
        subtotal = sum(item["quantity"] * item["price"] for item in items)
        tax = subtotal * 0.05  # 5% tax
        discount = subtotal * 0.02  # 2% discount
        total = subtotal + tax - discount
        return subtotal, tax, discount, total

    def generate_next_invoice_id(self):
        """Generate next sequential invoice ID"""
        last_invoice = self.invoices_collection.find().sort("invoice_id", -1).limit(1)
        last_invoice = list(last_invoice)
        
        if last_invoice:
            return last_invoice[0]["invoice_id"] + 1
        else:
            return 1

    def save_to_database(self, customer_name, customer_address, customer_number, items, subtotal, tax, discount, total):
        """Save invoice to MongoDB"""
        invoice_id = self.generate_next_invoice_id()
        
        invoice_doc = {
            "invoice_id": invoice_id,
            "customer_name": customer_name,
            "customer_address": customer_address,
            "customer_number": customer_number,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "discount": discount,
            "total": total,
            "order_date": datetime.now(),
            "created_at": datetime.now()
        }
        
        result = self.invoices_collection.insert_one(invoice_doc)
        return invoice_id

    def generate_invoice(self, filename, customer_name, customer_address, items, customer_number):
        """Generate PDF invoice"""
        shop_name = "SHAKIL'S GROCERY SHOP"
        shop_address = "Satellite Road, Ahmedabad, Gujarat - 380015"
        shop_contact = "+91 9725845511"
        shop_email = "kandhalshakil@shakil.com"
        shop_gst = "24ABCDE1234F2Z5"
        
        subtotal, tax, discount, total = self.calculate_totals(items)
        
        # Save invoice details to the database
        invoice_id = self.save_to_database(
            customer_name, customer_address, customer_number,
            items, subtotal, tax, discount, total
        )
        
        # Set the filename
        filename = f"{invoice_id}_{filename}"
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
        
        # Invoice ID
        c.setFont("Helvetica-Bold", 14)
        c.drawString(400, 665, f"Invoice ID: {invoice_id}")
        
        # Customer Info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 650, f"To: {customer_name}")
        c.drawString(50, 635, f"Address: {customer_address}")
        c.drawString(50, 620, f"Contact: {customer_number}")
        
        # Items table
        y = 580
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Item")
        c.drawString(200, y, "Quantity")
        c.drawString(280, y, "Price")
        c.drawString(350, y, "Total")
        c.line(50, y-5, 400, y-5)
        
        y -= 20
        c.setFont("Helvetica", 10)
        for item in items:
            c.drawString(50, y, item["name"])
            c.drawString(200, y, str(item["quantity"]))
            c.drawString(280, y, f"₹{item['price']:.2f}")
            c.drawString(350, y, f"₹{item['quantity'] * item['price']:.2f}")
            y -= 15
        
        # Totals
        y -= 10
        c.line(50, y, 400, y)
        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(280, y, f"Subtotal: ₹{subtotal:.2f}")
        y -= 15
        c.drawString(280, y, f"CGST (2.5%): ₹{tax/2:.2f}")
        y -= 15
        c.drawString(280, y, f"SGST (2.5%): ₹{tax/2:.2f}")
        y -= 15
        c.drawString(280, y, f"Discount (2%): -₹{discount:.2f}")
        y -= 15
        c.line(280, y, 400, y)
        y -= 15
        c.setFont("Helvetica-Bold", 12)
        c.drawString(280, y, f"Total Amount: ₹{total:.2f}")
        
        # Add GST number
        y -= 25
        c.setFont("Helvetica", 8)
        c.drawString(50, y, f"GST No: {shop_gst}")
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, "Thank you for your business!")
        
        c.save()
        return filename

    def generate_invoice_start(self):
        """Interactive invoice generation"""
        print("\n--- GENERATE INVOICE ---")
        customer_name = input("Enter customer name: ")
        customer_address = input("Enter customer address: ")
        customer_number = input("Enter customer contact number: ")
        
        items = []
        while True:
            print("\n--- ADD ITEMS TO INVOICE ---")
            self.view_items()
            
            try:
                item_id = input("Enter item ID (or 'done' to finish): ")
                if item_id.lower() == 'done':
                    break
                
                item = self.items_collection.find_one({"_id": ObjectId(item_id)})
                if not item:
                    print("Item not found.")
                    continue
                
                quantity = int(input(f"Enter quantity for {item['item_name']}: "))
                
                if quantity > item["stock"]:
                    print(f"Not enough stock. Available: {item['stock']}")
                    continue
                
                # Update stock
                self.items_collection.update_one(
                    {"_id": ObjectId(item_id)},
                    {"$inc": {"stock": -quantity}}
                )
                
                items.append({
                    "name": item["item_name"],
                    "quantity": quantity,
                    "price": item["item_price"]
                })
                
                print(f"Added {quantity} x {item['item_name']} to invoice.")
                
            except Exception as e:
                print(f"Error: {e}")
        
        if not items:
            print("No items added to invoice.")
            return None
        
        filename = f"invoice_{customer_name.replace(' ', '_').lower()}.pdf"
        return self.generate_invoice(filename, customer_name, customer_address, items, customer_number)

    def find_invoice_by_bill_number(self):
        """Find invoice by invoice ID"""
        invoice_id = int(input("Enter invoice ID: "))
        invoice = self.invoices_collection.find_one({"invoice_id": invoice_id})
        
        if not invoice:
            print("Invoice not found.")
            return
        
        print(f"\n--- INVOICE {invoice_id} ---")
        print(f"Customer: {invoice['customer_name']}")
        print(f"Address: {invoice['customer_address']}")
        print(f"Contact: {invoice['customer_number']}")
        print(f"Date: {invoice['order_date'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total: ₹{invoice['total']:.2f}")
        print("\nItems:")
        for item in invoice['items']:
            print(f"  {item['name']} - {item['quantity']} x ₹{item['price']:.2f} = ₹{item['quantity'] * item['price']:.2f}")

    def find_invoice(self):
        """Show all invoices"""
        invoices = list(self.invoices_collection.find().sort("invoice_id", -1))
        
        if not invoices:
            print("No invoices found.")
            return
        
        table_data = []
        for invoice in invoices:
            table_data.append([
                invoice["invoice_id"],
                invoice["customer_name"],
                invoice["order_date"].strftime("%Y-%m-%d"),
                f"₹{invoice['total']:.2f}"
            ])
        
        print(tabulate(table_data, headers=["Invoice ID", "Customer", "Date", "Total"], tablefmt="grid"))

    def display_sales_report(self):
        """Display sales statistics"""
        total_invoices = self.invoices_collection.count_documents({})
        total_revenue = list(self.invoices_collection.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]))
        
        print("\n--- SALES REPORT ---")
        print(f"Total Invoices: {total_invoices}")
        print(f"Total Revenue: ₹{total_revenue[0]['total']:.2f}" if total_revenue else "Total Revenue: ₹0.00")
        
        # Top customers
        top_customers = list(self.invoices_collection.aggregate([
            {"$group": {"_id": "$customer_name", "total_spent": {"$sum": "$total"}, "invoice_count": {"$sum": 1}}},
            {"$sort": {"total_spent": -1}},
            {"$limit": 5}
        ]))
        
        if top_customers:
            print("\n--- TOP CUSTOMERS ---")
            for customer in top_customers:
                print(f"{customer['_id']}: ₹{customer['total_spent']:.2f} ({customer['invoice_count']} invoices)")

    def display_sales_graph(self):
        """Display sales graph"""
        try:
            # Get daily sales for the last 30 days
            pipeline = [
                {
                    "$group": {
                        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}},
                        "daily_sales": {"$sum": "$total"}
                    }
                },
                {"$sort": {"_id": 1}},
                {"$limit": 30}
            ]
            
            daily_sales = list(self.invoices_collection.aggregate(pipeline))
            
            if not daily_sales:
                print("No sales data available for graph.")
                return
            
            dates = [item["_id"] for item in daily_sales]
            sales = [item["daily_sales"] for item in daily_sales]
            
            plt.figure(figsize=(12, 6))
            plt.plot(dates, sales, marker='o')
            plt.title("Daily Sales Report")
            plt.xlabel("Date")
            plt.ylabel("Sales ($)")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            print(f"Error generating graph: {e}")

    def exit_program(self):
        """Close database connection and exit"""
        self.client.close()
        print("Thank you for using Shakil Grocery Shop! Goodbye.")
        exit()

    def run(self):
        """Main program loop"""
        while True:
            try:
                self.run_menu()
            except ValueError:
                print("Error: Invalid input. Please try again.")
                continue
            except KeyboardInterrupt:
                print("\nExiting program...")
                self.exit_program()

    def run_menu(self):
        """Display menu and handle user choice"""
        print("\n" + "="*60)
        print("🏪    SHAKIL'S GROCERY SHOP - MAIN MENU    🇮🇳")
        print("        Satellite Road, Ahmedabad, Gujarat")
        print("="*60)
        print("1.  Add Item")
        print("2.  View Items")
        print("3.  Update Item")
        print("4.  Remove Item")
        print("5.  Generate Invoice")
        print("6.  Display Sales Graph")
        print("7.  Display Sales Report")
        print("8.  Find Invoice by ID")
        print("9.  Search Item")
        print("10. Show All Invoices")
        print("11. Exit")
        print("="*50)
        
        choice = int(input("Enter your choice (1-11): "))
        
        if choice == 1:
            self.add_items()
        elif choice == 2:
            self.view_items()
        elif choice == 3:
            self.update_item()
        elif choice == 4:
            self.remove_item()
        elif choice == 5:
            filename = self.generate_invoice_start()
            if filename and input("Do you want to open the invoice PDF? (Y/N): ").upper() == "Y":
                webbrowser.open(filename)
        elif choice == 6:
            self.display_sales_graph()
        elif choice == 7:
            self.display_sales_report()
        elif choice == 8:
            self.find_invoice_by_bill_number()
        elif choice == 9:
            self.search_item()
        elif choice == 10:
            self.find_invoice()
        elif choice == 11:
            self.exit_program()
        else:
            print("Invalid choice. Please select 1-11.")


if __name__ == "__main__":
    try:
        invoice_generator = MongoDB_Invoice_Generator()
        print("Welcome to Shakil Grocery Shop!")
        invoice_generator.run()
    except Exception as e:
        print(f"Error starting application: {e}")