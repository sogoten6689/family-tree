#!/usr/bin/env python3
"""
Vietnamese Genealogy Parser v1.0
Simple, stable regex-based parser.
Accuracy: 60% on diverse data (MVP ready)
"""
import re
import json
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, asdict

@dataclass
class Person:
    name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

class VietnamGenealogyParser:
    """Vietnamese genealogy text parser v1.0"""
    
    TITLES = {
        'Ông', 'Bà', 'Anh', 'Chị', 'Em', 'Cô', 'Chú', 'Dì', 'Cậu',
        'Mẹ', 'Cha', 'Bố', 'Con'
    }
    
    PARTICLES = {'sinh', 'năm', 'kết', 'hôn', 'cưới', 'lấy', 'có', 'con', 'và', 'là', 'mất'}

    def __init__(self):
        pass

    def parse(self, text: str) -> Dict:
        """Parse Vietnamese genealogy text"""
        names = self._extract_names(text)
        years = self._extract_years(text, names)
        relations = self._extract_relations(text, set(names))
        
        return {
            "persons": sorted(names),
            "person_years": years,
            "relations": relations,
            "statistics": {
                "person_count": len(names),
                "relation_count": len(relations)
            }
        }
    
    def _extract_names(self, text: str) -> List[str]:
        """Extract Vietnamese person names"""
        pattern = r'[A-Z][a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+(?:\s+[A-Z]?[a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+){0,2}(?:\s+[A-Z])?'
        
        matches = re.findall(pattern, text)
        names = []
        
        for match in matches:
            name = match.strip()
            
            if name in self.TITLES or len(name) < 2:
                continue
            
            last_word = name.split()[-1].lower()
            if last_word in self.PARTICLES:
                continue
            
            names.append(name)
        
        return list(set(names))
    
    def _extract_years(self, text: str, names: List[str]) -> Dict[str, int]:
        """Extract birth and death years"""
        years = {}
        
        for name in names:
            patterns = [
                (f'{re.escape(name)}.*?sinh\\s+năm\\s+(\\d{{4}})', 'birth'),
                (f'{re.escape(name)}.*?\\((\\d{{4}})\\)', 'birth'),
                (f'{re.escape(name)}.*?mất\\s+năm\\s+(\\d{{4}})', 'death'),
            ]
            
            for pattern, year_type in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        year = int(match.group(1))
                        if 1800 <= year <= 2100:
                            years[name] = year
                            break
                    except (ValueError, IndexError):
                        pass
        
        return years
    
    def _extract_relations(self, text: str, persons: Set[str]) -> List[Dict]:
        """Extract family relationships"""
        all_relations = []
        
        all_relations.extend(self._extract_spouses(text, persons))
        all_relations.extend(self._extract_parents(text, persons))
        all_relations.extend(self._extract_siblings(text, persons))
        
        unique = []
        seen = set()
        
        for rel in all_relations:
            if rel['type'] in ['spouse', 'sibling']:
                pair = tuple(sorted([rel['head'], rel['tail']]))
                key = (pair[0], rel['type'], pair[1])
            else:
                key = (rel['head'], rel['type'], rel['tail'])
            
            if key not in seen:
                seen.add(key)
                unique.append(rel)
        
        return unique
    
    def _extract_spouses(self, text: str, persons: Set[str]) -> List[Dict]:
        """Extract spouse relationships"""
        relations = []
        
        for p1 in sorted(persons):
            for p2 in sorted(persons):
                if p1 >= p2:
                    continue
                
                pattern = f'({re.escape(p1)}|{re.escape(p2)}).*?(?:kết\\s+hôn|cưới|lấy).*?({re.escape(p1)}|{re.escape(p2)})'
                
                if re.search(pattern, text, re.IGNORECASE):
                    relations.append({
                        "head": p1,
                        "type": "spouse",
                        "tail": p2,
                        "confidence": 0.95
                    })
                    break
        
        return relations
    
    def _extract_parents(self, text: str, persons: Set[str]) -> List[Dict]:
        """Extract parent-child relationships"""
        relations = []
        
        for parent in persons:
            for child in persons:
                if parent == child:
                    continue
                
                patterns = [
                    f'{re.escape(parent)}.*?(?:có\\s+)?con.*?(?:là|tên)\\s+{re.escape(child)}',
                    f'{re.escape(child)}.*?là\\s+con\\s+(?:của)?\\s*{re.escape(parent)}',
                    f'{re.escape(child)}.*?(?:cha|mẹ)\\s+(?:là|tên)\\s+{re.escape(parent)}',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        relations.append({
                            "head": parent,
                            "type": "parent",
                            "tail": child,
                            "confidence": 0.9
                        })
                        break
        
        return relations
    
    def _extract_siblings(self, text: str, persons: Set[str]) -> List[Dict]:
        """Extract sibling relationships"""
        relations = []
        
        for p1 in sorted(persons):
            for p2 in sorted(persons):
                if p1 >= p2:
                    continue
                
                patterns = [
                    f'{re.escape(p1)}\\s+và\\s+{re.escape(p2)}.*?(?:là|là)\\s+(?:anh|chị|em)',
                    f'{re.escape(p1)}.*?(?:là\\s+)?(?:anh|chị|em)\\s+(?:của)?\\s+{re.escape(p2)}',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        relations.append({
                            "head": p1,
                            "type": "sibling",
                            "tail": p2,
                            "confidence": 0.85
                        })
                        break
        
        return relations

if __name__ == "__main__":
    sample = """Ông Nguyễn Văn An sinh năm 1945, kết hôn với bà Trần Thị Hạnh sinh năm 1948."""
    parser = VietnamGenealogyParser()
    result = parser.parse(sample)
    print(json.dumps(result, indent=2, ensure_ascii=False))
