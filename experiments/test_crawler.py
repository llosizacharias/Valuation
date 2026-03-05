from data_layer.ri_crawler import RICrawler

crawler = RICrawler("https://ri.weg.net", headless=False)
pdf_links = crawler.extract_pdf_links()

for link in pdf_links[:10]:
    print(link)