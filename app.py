import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.ttk import Progressbar
import requests
from bs4 import BeautifulSoup
import pandas as pd
import threading
import asyncio
import aiohttp
import matplotlib.pyplot as plt
from io import BytesIO
import zipfile
import sqlite3
import json
from datetime import datetime
import customtkinter as ctk  # Nowoczesne GUI

class WebScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zaawansowany Web Scraper")
        self.root.geometry("1200x900")
        ctk.set_appearance_mode("System")  # Tryb ciemny/jasny
        self.db_connection = sqlite3.connect("scraper_history.db")
        self.create_tables()
        self.create_widgets()

    def create_tables(self):
        cursor = self.db_connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                timestamp TEXT,
                results TEXT
            )
        """)
        self.db_connection.commit()

    def create_widgets(self):
        # Główna ramka
        frame = ctk.CTkFrame(self.root)
        frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(frame, text="Podaj URL(e):").grid(row=0, column=0, padx=10, pady=5)
        self.url_entry = ctk.CTkEntry(frame, width=800)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Tag do scrapowania:").grid(row=1, column=0, padx=10, pady=5)
        self.tag_combobox = ttk.Combobox(frame, values=["a", "div", "p", "span", "img", "h1", "h2", "h3"])
        self.tag_combobox.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Atrybut (opcjonalnie):").grid(row=2, column=0, padx=10, pady=5)
        self.attribute_entry = ctk.CTkEntry(frame, width=800)
        self.attribute_entry.grid(row=2, column=1, padx=10, pady=5)

        self.scrape_button = ctk.CTkButton(frame, text="Rozpocznij Scrapowanie", command=self.start_scraping)
        self.scrape_button.grid(row=3, column=1, padx=10, pady=10)

        self.progress = Progressbar(frame, orient="horizontal", mode="determinate", length=400)
        self.progress.grid(row=4, column=1, padx=10, pady=5)

        self.raw_html_button = ctk.CTkButton(frame, text="Pokaż surowy HTML", command=self.show_raw_html)
        self.raw_html_button.grid(row=5, column=1, padx=10, pady=10)

        # Historia scrapingów
        history_frame = ctk.CTkFrame(self.root)
        history_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(history_frame, text="Historia scrapingów:").pack(anchor="w")
        self.history_listbox = ctk.CTkTextbox(history_frame, height=100)
        self.history_listbox.pack(fill="x", padx=10, pady=5)

        # Wyniki
        results_frame = ctk.CTkFrame(self.root)
        results_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.tree = ttk.Treeview(results_frame, columns=("Tag", "Attributes", "Content"), show="headings", height=25)
        self.tree.heading("Tag", text="Tag")
        self.tree.heading("Attributes", text="Atrybuty")
        self.tree.heading("Content", text="Zawartość")
        self.tree.column("Tag", width=100)
        self.tree.column("Attributes", width=200)
        self.tree.column("Content", width=600)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # Eksportowanie
        export_frame = ctk.CTkFrame(self.root)
        export_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkButton(export_frame, text="Eksportuj do CSV", command=self.export_to_csv).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(export_frame, text="Eksportuj do PDF", command=self.export_to_pdf).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(export_frame, text="Eksportuj do ZIP", command=self.export_to_zip).pack(side="left", padx=10, pady=5)

    def scrape_data(self, urls, tag, attribute):
        results = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.scrape_async(urls, tag, attribute, results))
        return results

    async def scrape_async(self, urls, tag, attribute, results):
        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(urls):
                try:
                    async with session.get(url.strip()) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        elements = soup.find_all(tag, {attribute: True} if attribute else None)
                        for element in elements:
                            attributes = json.dumps(element.attrs)
                            results.append((tag, attributes, element.text.strip()))
                except Exception as e:
                    results.append((f"Błąd w {url.strip()}", "", str(e)))

                # Aktualizacja paska postępu
                self.progress['value'] = ((i + 1) / len(urls)) * 100
                self.root.update_idletasks()

    def start_scraping(self):
        url_text = self.url_entry.get()
        urls = url_text.split(",") if url_text else []
        tag = self.tag_combobox.get()
        attribute = self.attribute_entry.get()

        if not urls or not tag:
            messagebox.showerror("Błąd", "Podaj URL(e) oraz tag!")
            return

        self.progress['value'] = 0
        self.tree.delete(*self.tree.get_children())

        # Wątek do scrapowania
        thread = threading.Thread(target=self.scraping_thread, args=(urls, tag, attribute))
        thread.start()

    def scraping_thread(self, urls, tag, attribute):
        results = self.scrape_data(urls, tag, attribute)
        for result in results:
            self.tree.insert("", "end", values=result)
        self.save_scraping_history(urls, results)

    def save_scraping_history(self, urls, results):
        cursor = self.db_connection.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO scraping_history (url, timestamp, results) VALUES (?, ?, ?)",
                       (", ".join(urls), timestamp, json.dumps(results)))
        self.db_connection.commit()
        self.history_listbox.insert("end", f"{timestamp}: {', '.join(urls)}\n")

    def show_raw_html(self):
        file_path = filedialog.askopenfilename(filetypes=[("HTML files", "*.html"), ("All files", "*.*")])
        if not file_path:
            return
        with open(file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
        raw_html_window = tk.Toplevel(self.root)
        raw_html_window.title("Surowy HTML")
        text_widget = ctk.CTkTextbox(raw_html_window, wrap="none")
        text_widget.insert("1.0", html_content)
        text_widget.pack(fill="both", expand=True)

    def export_to_csv(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        try:
            data = [{"Tag": self.tree.item(row)["values"][0],
                     "Attributes": self.tree.item(row)["values"][1],
                     "Content": self.tree.item(row)["values"][2]}
                    for row in self.tree.get_children()]
            pd.DataFrame(data).to_csv(file_path, index=False)
            messagebox.showinfo("Sukces", "Dane wyeksportowane do CSV!")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się eksportować: {e}")

    def export_to_pdf(self):
        messagebox.showinfo("Info", "Eksport PDF w wersji premium!")

    def export_to_zip(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return
        try:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                data = [{"Tag": self.tree.item(row)["values"][0],
                         "Attributes": self.tree.item(row)["values"][1],
                         "Content": self.tree.item(row)["values"][2]}
                        for row in self.tree.get_children()]
                zip_file.writestr("scraped_data.json", json.dumps(data, indent=4))

            with open(file_path, "wb") as f:
                f.write(zip_buffer.getvalue())

            messagebox.showinfo("Sukces", "Dane wyeksportowane do ZIP!")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się eksportować: {e}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = WebScraperApp(root)
    root.mainloop()
