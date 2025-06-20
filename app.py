# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "monsterui",
#     "python-fasthtml",
# ]
# ///
from fasthtml.common import *
from monsterui.all import *
import json

with open('evals.json', 'r') as f: evals = json.load(f)

# Initialize annotation fields if they don't exist
for eval_item in evals:
    if 'ground_truth_annotations' not in eval_item:
        eval_item['ground_truth_annotations'] = [False] * len(eval_item['ground_truth_components'])
    if 'haiku_annotations' not in eval_item:
        eval_item['haiku_annotations'] = {
            'exact': [False] * len(eval_item['haiku_components']),
            'partial': [False] * len(eval_item['haiku_components']),
            'extra': [False] * len(eval_item['haiku_components']),
            'hallucination': [False] * len(eval_item['haiku_components'])
        }

app, rt = fast_app(hdrs=Theme.blue.headers())

def save_evals():
    with open('evals.json', 'w') as f: json.dump(evals, f, indent=2)

def ground_truth_table(eval_item, idx):
    headers = ["Ground Truth Components", "Missing"]
    
    def ground_truth_row(i, component):
        return Tr(
            Td(f"{i+1}. {component}", cls=TextPresets.muted_sm),
            Td(CheckboxX(name=f"ground_truth_{i}_missing", checked=eval_item['ground_truth_annotations'][i],
                        hx_post=f"/update_ground_truth/{idx}/{i}", hx_swap="none")))
    
    return Table(
        Thead(Tr(*[Th(h) for h in headers])),
        Tbody(*[ground_truth_row(i, comp) for i, comp in enumerate(eval_item['ground_truth_components'])]),
        cls=TableT.striped)

def haiku_table(eval_item, idx):
    headers = ["Haiku Components", "Exact match", "Partial match", "Extra Components", "Hallucinations"]
    
    def haiku_row(i, component):
        return Tr(
            Td(f"{i+1}. {component}", cls=TextPresets.muted_sm),
            *[Td(CheckboxX(name=f"haiku_{i}_{cat}", checked=eval_item['haiku_annotations'][cat][i],
                          hx_post=f"/update_haiku/{idx}/{i}/{cat}", hx_swap="none")) 
              for cat in ["exact", "partial", "extra", "hallucination"]])
    
    return Table(
        Thead(Tr(*[Th(h) for h in headers])),
        Tbody(*[haiku_row(i, comp) for i, comp in enumerate(eval_item['haiku_components'])]),
        cls=TableT.striped)

def navigation_buttons(idx):
    prev_btn = A("Previous", href=f"/{idx-1}", cls=ButtonT.secondary) if idx > 0 else Button("Previous", disabled=True, cls=ButtonT.secondary)
    next_btn = A("Next", href=f"/{idx+1}", cls=ButtonT.primary) if idx < len(evals)-1 else Button("Next", disabled=True, cls=ButtonT.primary)
    return DivFullySpaced(prev_btn, P(f"Question {idx+1} of {len(evals)}", cls=TextPresets.muted_sm), next_btn)

def question_display(eval_item, idx):
    return Container(
        navigation_buttons(idx),
        H3("Question"),
        P(eval_item['question_text'], cls=TextPresets.muted_lg),
        H3("Gold Standard Answer"),
        P(eval_item['gold_standard_answer'], cls=TextPresets.muted_sm),
        H3("Ground Truth Components"),
        ground_truth_table(eval_item, idx),
        H3("Haiku Components Annotation"),
        haiku_table(eval_item, idx))

@rt
def index(): return RedirectResponse("0")

@rt("/{idx}")
def question(idx: int):
    if idx < 0 or idx >= len(evals): return RedirectResponse("0")
    return Titled("Component Annotation Tool", question_display(evals[idx], idx))

@rt("/update_ground_truth/{idx}/{comp_idx}")
def update_ground_truth(idx: int, comp_idx: int):
    evals[idx]['ground_truth_annotations'][comp_idx] = not evals[idx]['ground_truth_annotations'][comp_idx]
    save_evals()
    return ""

@rt("/update_haiku/{idx}/{comp_idx}/{category}")
def update_haiku(idx: int, comp_idx: int, category: str):
    evals[idx]['haiku_annotations'][category][comp_idx] = not evals[idx]['haiku_annotations'][category][comp_idx]
    save_evals()
    #return ""

    def analyze_annotations(evals):
        # Component-level counts
        component_counts = {
            'exact': 0,
            'partial': 0, 
            'extra': 0,
            'hallucination': 0,
            'missing': 0
        }
        
        # Question-level counts (questions with at least one component in each category)
        question_counts = {
            'exact': 0,
            'partial': 0,
            'extra': 0, 
            'hallucination': 0,
            'missing': 0
        }

        
        for eval_item in evals:
            # Skip if no annotations exist
            if 'haiku_annotations' not in eval_item or 'ground_truth_annotations' not in eval_item:
                continue
                
            # Count components
            for category in ['exact', 'partial', 'extra', 'hallucination']:
                component_counts[category] += sum(eval_item['haiku_annotations'][category])
                
            component_counts['missing'] += sum(eval_item['ground_truth_annotations'])
            
            # Count questions with at least one component in each category
            for category in ['exact', 'partial', 'extra', 'hallucination']:
                if any(eval_item['haiku_annotations'][category]):
                    question_counts[category] += 1
                    
            if any(eval_item['ground_truth_annotations']):
                question_counts['missing'] += 1
        
        return component_counts, question_counts

    component_counts, question_counts = analyze_annotations(evals)

    print("Component-level Analysis:")
    print("Category\t\tCount")
    print("-" * 25)
    for category, count in component_counts.items():
        print(f"{category.capitalize():<15}\t{count}")

    print("\nQuestion-level Analysis (questions with at least one component):")
    print("Category\t\tCount")
    print("-" * 25)
    for category, count in question_counts.items():
        print(f"{category.capitalize():<15}\t{count}")

    print(f"\nTotal questions analyzed: {len([e for e in evals if 'haiku_annotations' in e])}")

    return ""

serve()
