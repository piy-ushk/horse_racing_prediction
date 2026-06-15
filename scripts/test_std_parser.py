import requests
from html.parser import HTMLParser

class NetkeibaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_umaban = False
        self.in_horse_name = False
        self.in_a = False
        self.current_umaban = None
        self.current_horse_name = None
        self.map = {}
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "td":
            cls = attrs_dict.get("class", "")
            if cls.startswith("Umaban"):
                self.in_umaban = True
        elif tag == "span":
            cls = attrs_dict.get("class", "")
            if "HorseName" in cls:
                self.in_horse_name = True
        elif tag == "a" and self.in_horse_name:
            self.in_a = True
            
    def handle_data(self, data):
        data = data.strip()
        if not data: return
        if self.in_umaban:
            try: self.current_umaban = int(data)
            except ValueError: pass
        elif self.in_a:
            self.current_horse_name = data
            
    def handle_endtag(self, tag):
        if tag == "td" and self.in_umaban:
            self.in_umaban = False
        elif tag == "a" and self.in_a:
            self.in_a = False
        elif tag == "span" and self.in_horse_name:
            self.in_horse_name = False
            if self.current_umaban is not None and self.current_horse_name is not None:
                self.map[self.current_umaban] = self.current_horse_name
                self.current_umaban = None
                self.current_horse_name = None

def test():
    url = "https://nar.netkeiba.com/race/shutuba.html?race_id=202630060801"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    parser = NetkeibaParser()
    parser.feed(resp.text)
    print(len(parser.map))

if __name__ == "__main__":
    test()
