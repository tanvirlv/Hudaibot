"""
Calculator Command
"""

import re
import logging

def transform_percentage(expression):
    expr = expression.replace(" ", "")
    
    if '%' not in expr:
        return expr
    
    expr = re.sub(r'\*(\d+\.?\d*)%', r'*(\1/100)', expr)
    expr = re.sub(r'/(\d+\.?\d*)%', r'/(\1/100)', expr)
    
    def replace_plus_minus_percent(match):
        a = match.group(1)
        op = match.group(2)
        b = match.group(3)
        return a + op + '(' + a + '*' + b + '/100)'
    
    pattern_plus_minus = r'(\d+\.?\d*)([+\-])(\d+\.?\d*)%'
    
    prev = ""
    while prev != expr:
        prev = expr
        expr = re.sub(pattern_plus_minus, replace_plus_minus_percent, expr, count=1)
    
    expr = re.sub(r'(\d+\.?\d*)%', r'(\1/100)', expr)
    
    return expr

def safe_calculate(expression):
    expression = expression.replace(" ", "")
    
    if not expression:
        raise ValueError("Empty expression")
    
    allowed_pattern = r'^[\d+\-*/().%]+$'
    if not re.match(allowed_pattern, expression):
        raise ValueError("Invalid characters in expression")
    
    expression = transform_percentage(expression)
    
    clean_expr = expression.replace('(-', '(0-').replace('--', '+')
    if clean_expr.startswith('-'):
        clean_expr = '0' + clean_expr
    
    try:
        result = eval(clean_expr, {"__builtins__": {}}, {})
        return result
    except Exception as e:
        raise ValueError("Invalid expression: {}".format(str(e)))

def format_calc_result(result):
    if isinstance(result, float):
        if result.is_integer():
            return "{:,}".format(int(result))
        else:
            rounded = round(result, 6)
            return "{:,.6f}".format(rounded).rstrip('0').rstrip('.')
    elif isinstance(result, int):
        return "{:,}".format(result)
    else:
        return str(result)

def register(client, prefix):
    """Register calculator command"""
    
    from telethon import events
    
    @client.on(events.NewMessage(pattern=r'^([\d+\-*/().%\s]+)$'))
    async def calc_handler(event):
        """Calculator command"""
        
        try:
            expression = event.pattern_match.group(1).strip()
            
            # Skip if message is too short or doesn't look like a calculation
            if len(expression) < 3:
                return
            
            # Must contain at least one operator
            if not any(op in expression for op in ['+', '-', '*', '/', '%']):
                return
            
            allowed_chars = set('0123456789+-*/().% ')
            if not all(char in allowed_chars for char in expression):
                await event.respond("```\n✗ Iɴᴠᴀʟɪᴅ Cʜᴀʀᴀᴄᴛᴇʀs Iɴ Exᴘʀᴇssɪᴏɴ!\n\nAʟʟᴏᴡᴇᴅ: Nᴜᴍʙᴇʀs, +, -, *, /, (, ), ., %\n\nExᴀᴍᴘʟᴇ: 120+22\n```")
                return
            
            if not expression or expression.isspace():
                return
            
            original_expr = expression
            
            result = safe_calculate(expression)
            formatted_result = format_calc_result(result)
            
            lines = []
            lines.append("✓ Cᴀʟᴄᴜʟᴀᴛɪᴏɴ Cᴏᴍᴘʟᴇᴛᴇ")
            lines.append("➦Iɴᴘᴜᴛ : {}".format(original_expr))
            lines.append("➥Rᴇsᴜʟᴛ: {}".format(formatted_result))
            lines.append("━━━━━━━━━━━━━━━━━━")
            
            await event.respond("\n".join(lines))
            
        except ZeroDivisionError:
            await event.respond("```\n✗ Eʀʀᴏʀ: Dɪᴠɪsɪᴏɴ Bʏ Zᴇʀᴏ!\n```")
        except ValueError as ve:
            await event.respond("```\n✗ Eʀʀᴏʀ: {}\n\nExᴀᴍᴘʟᴇ: 120+22\n```".format(str(ve)))
        except SyntaxError:
            await event.respond("```\n✗ Eʀʀᴏʀ: Iɴᴠᴀʟɪᴅ Exᴘʀᴇssɪᴏɴ Sʏɴᴛᴀx!\n\nExᴀᴍᴘʟᴇ: 120+22\n```")
        except Exception as e:
            logging.error("Calculator Command Error: {}".format(e))
            return  # Silently ignore other errors
