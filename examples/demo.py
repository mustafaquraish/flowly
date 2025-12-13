import sys
import os

# Ensure flowly is in path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from flowly.frontend import FlowBuilder
from flowly.engine import FlowRunner

def main():
    print("Building Flowchart...")
    builder = FlowBuilder("Pizza Order")
    
    start = builder.start("Start")
    
    choose_pizza = builder.action("Choose Pizza")
    builder.connect(start, choose_pizza)
    
    is_delivery = builder.decision("Is it delivery?")
    builder.connect(choose_pizza, is_delivery)
    
    enter_address = builder.action("Enter Address")
    builder.connect(is_delivery, enter_address, label="Yes")
    
    takeout = builder.action("Go to shop")
    builder.connect(is_delivery, takeout, label="No")
    
    pay = builder.action("Pay")
    builder.connect(enter_address, pay)
    builder.connect(takeout, pay)
    
    end = builder.end("Enjoy Pizza")
    builder.connect(pay, end)
    
    chart = builder.build()
    print(f"Flowchart built with {len(chart.nodes)} nodes and {len(chart.edges)} edges.")
    
    print("\nRunning Flowchart...")
    runner = FlowRunner(chart)
    runner.start()
    
    while runner.current_node:
        print(f"Current Node: {runner.current_node.label} ({runner.current_node.__class__.__name__})")
        
        from flowly.core import EndNode, DecisionNode
        if isinstance(runner.current_node, EndNode):
            break
            
        options = runner.get_options()
        if len(options) == 0:
            print("Dead end.")
            break
        elif len(options) == 1:
            print(f"  -> Auto advancing via '{options[0].label or 'next'}'")
            runner.step()
        else:
            print("  Choices:")
            for i, opt in enumerate(options):
                print(f"    [{i}] {opt.label or 'Next'} -> {chart.get_node(opt.target_id).label}")
            
            # Simple simulation: always pick 0 for now, or prompt?
            # Let's prompt for interactive check
            try:
                choice = int(input("  Enter choice: "))
                runner.choose_path(choice)
            except (ValueError, IndexError):
                print("Invalid choice, exiting.")
                break
                
    print("Done.")

if __name__ == "__main__":
    main()
