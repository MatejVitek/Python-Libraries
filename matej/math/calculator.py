import operator as op
import math
import string
from itertools import chain
from enum import Enum

import . as utils


Associativity = Enum('Associativity', 'LEFT RIGHT')
Arity = Enum('Arity', 'UNARY BINARY')


class Token:
    def __init__(self, s, group=None):
        self.str = (s,) if isinstance(s, str) else s
        if group is not None:
            group.append(self)

    def __str__(self):
        return self.str[0]


brackets = []
LBR = Token(('(', '['), brackets)
RBR = Token((')', ']'), brackets)
LABS = Token('|', brackets)
RABS = Token('|', brackets)
brackets = tuple(brackets)


class Number(Token):
    def __init__(self, value, s=None, group=None):
        super().__init__(s if s else str(value), group)
        self.value = value


constants = []
PI = Number(math.pi, ('π', 'pi'), constants)
E = Number(math.e, 'e', constants)
LIGHT_SPEED = Number(299792458.0, 'c', constants)
GRAVITY_ACCELERATION = Number(9.80665, 'g', constants)
GRAVITY_CONSTANT = Number(6.67384e-11, 'G', constants)
PLANCK = Number(6.62606957e-34, 'h', constants)
constants = tuple(constants)


operators = []


class Operator(Token):
    def __init__(self, s, f, precedence, associativity=Associativity.LEFT, arity=Arity.BINARY, group=operators):
        super().__init__(s, group)
        self.f = f
        self.precedence = precedence
        self.associativity = associativity
        self.arity = arity


PLUS = Operator('+', op.add, 0)
UPLUS = Operator('+', lambda x: x, 10, Associativity.RIGHT, Arity.UNARY)
MIN = Operator('-', op.sub, 0)
UMIN = Operator(('-', '~'), op.neg, 10, Associativity.RIGHT, Arity.UNARY)
MULT = Operator(('·', '⋅', '*', '×', 'x'), op.mul, 20)
DIV = Operator(('/', '÷'), op.truediv, 20)
IDIV = Operator(('//', 'div'), op.floordiv, 20)
MOD = Operator(('%', 'mod'), op.mod, 20)
FACT = Operator('!', math.factorial, 50, arity=Arity.UNARY)
DFACT = Operator('!!', utils.dfactorial, 50, arity=Arity.UNARY)
DEG = Operator(('°', 'deg'), lambda x: x * math.pi / 180.0, 50, arity=Arity.UNARY)
POW = Operator(('^', '**', 'pow'), op.pow, 30, Associativity.RIGHT)
SIN = Operator('sin', math.sin, 40, Associativity.RIGHT, Arity.UNARY)
COS = Operator('cos', math.cos, 40, Associativity.RIGHT, Arity.UNARY)
TAN = Operator(('tan', 'tg'), math.tan, 40, Associativity.RIGHT, Arity.UNARY)
CTG = Operator(('ctg', 'ctan', 'cotan'), lambda x: 1.0 / math.tan(x), 40, Associativity.RIGHT, Arity.UNARY)
LOG = Operator(('log', 'ln'), math.log, 40, Associativity.RIGHT, Arity.UNARY)
ABS = Operator('abs', abs, 40, Associativity.RIGHT, Arity.UNARY)
FLOOR = Operator(('fl', 'floor'), math.floor, 40, Associativity.RIGHT, Arity.UNARY)
CEIL = Operator(('ceil', 'ceiling'), math.ceil, 40, Associativity.RIGHT, Arity.UNARY)
SQ = Operator('sq', lambda x: x * x, 40, Associativity.RIGHT, Arity.UNARY)
SQRT = Operator('sqrt', math.sqrt, 40, Associativity.RIGHT, Arity.UNARY)
CMB = Operator(('C', 'cmb', 'choose'), utils.ncr, 25)
N_LOG = Operator(('nlog', 'log', 'loga'), lambda x, y: math.log(y, x), 25, Associativity.RIGHT)
N_RT = Operator(('rt', 'nrt'), lambda x, y: math.pow(y, 1.0 / x), 25, Associativity.RIGHT)

# Test operators
LAB0 = Operator('+', op.add, 0)
LAB1 = Operator('+', op.add, 1)
RAB0 = Operator('**', op.add, 0, Associativity.RIGHT)
RAB1 = Operator('**', op.add, 1, Associativity.RIGHT)
LAU0 = Operator('!', op.neg, 0, arity=Arity.UNARY)
LAU1 = Operator('!', op.neg, 1, arity=Arity.UNARY)
RAU0 = Operator('-', math.factorial, 0, Associativity.RIGHT, Arity.UNARY)
RAU1 = Operator('-', math.factorial, 1, Associativity.RIGHT, Arity.UNARY)


operators = tuple(operators)


def main():
    print("Input q to quit.")
    while True:
        exp = input("Input expression: ")
        if not exp:
            continue
        if exp.lower() in ('q', 'quit', 'exit'):
            break

        try:
            print(calculate(exp))
        except ValueError as e:
            print(e)


def calculate(exp):
    tokens = _prepare(exp)
    if not tokens:
        return ""
    rpn = _shunting_yard(tokens)
    return _evaluate(rpn)


def prepare(exp):
    return _detokenize(_prepare(exp))


def _prepare(exp):
    tokens = _tokenize(exp)
    _replace_abs_brackets(tokens)
    return tokens


def _tokenize(exp):
    tokens = []
    i = 0
    token = None
    while i < len(exp):
        while i < len(exp) and exp[i].isspace():
            i += 1
        if i < len(exp):
            token, length = _get_token(exp, i, token)
            tokens.append(token)
            i += length
    return tokens


def _detokenize(tokens):
    return "".join(_pretty_print(t) for t in tokens)


def _pretty_print(t):
    s = str(t)
    if isinstance(t, Operator):
        if t.arity is Arity.BINARY:
            return " " + s + " "
        return s + " " if t.associativity is Associativity.LEFT else " " + s
    return s


def _get_token(exp, pos, prev_token):
    if pos < 0 or pos >= len(exp):
        return None, 0

    # special handling for abs value brackets
    if exp[pos] == '|':
        return (LABS, 1) if _is_labs(exp, pos) else (RABS, 1)

    if exp[pos].isdecimal():
        return _get_number(exp, pos)

    matches = [
        (t, s)
        for t in chain(brackets, constants, operators) for s in t.str
        if exp.lower().startswith(s.lower(), pos)
    ]

    # filter out operators with incorrect arity and unary operators with incorrect associativity
    matches = [
        (t, s)
        for t, s in matches
        if not isinstance(t, Operator) or _check_arity(exp, pos, t, len(s), prev_token)
    ]

    if not matches:
        return None, 0

    # filter out tokens with length lower than maximal
    if len(matches) > 1:
        m = max(len(s) for _, s in matches)
        matches = [(t, s) for t, s in matches if len(s) == m]

    # filter out tokens with incorrect capitalisation
    if len(matches) > 1:
        matches = [(t, s) for t, s in matches if exp.startswith(s, pos)]

    if not matches:
        return None, 0

    return matches[0][0], len(matches[0][1])


def _is_labs(exp, pos):
    i = pos - 1

    # find the nearest unclosed left bracket
    depth = 0
    while i > 0 and depth >= 0:
        if exp[i] in LBR.str:
            depth -= 1
        elif exp[i] in RBR.str:
            depth += 1
        i -= 1

    return exp.count('|', i, pos) % 2 == 0


def _get_number(exp, pos):
    i = pos
    base = 10
    digits = string.digits
    x = 0

    if exp[i] == '0' and i < len(exp) - 1:
        i += 1
        if exp[i].lower() in 'bx':
            base = 2 if exp[i].lower() == 'b' else 16
            digits = '01' if exp[i].lower() == 'b' else string.hexdigits
            pos += 1
        else:
            base = 8
            digits = string.octdigits
            if exp[i].lower() == 'o':
                i += 1

    while i < len(exp) and exp[i] in digits:
        x *= base
        x += int(exp[i], base)
        i += 1

    if i < len(exp) and exp[i] == '.':
        i += 1
        p = 1.0 / base
        while i < len(exp) and exp[i] in digits:
            x += int(exp[i], base) * p
            p /= base
            i += 1

    if i < len(exp) - 1 and exp[i].lower() == 'e' and exp[i + 1] in chain(digits, UPLUS.str, UMIN.str):
        i += 1
        sign = 1
        p = 0
        if exp[i] in chain(UPLUS.str, UMIN.str):
            if exp[i] in UMIN.str:
                sign = -1
            i += 1
        while i < len(exp) and exp[i] in digits:
            p *= base
            p += int(exp[i], base)
            i += 1
        x *= math.pow(base, sign * p)

    return Number(x), i - pos


# NOTE: this requires that implicit multiplication should not be allowed with operators (3log9 =/= 3 * log9)
def _check_arity(exp, pos, t, t_len, left_token):
    # shorthands for whether the operator o is binary, left-associative unary, or right-associative unary
    def bin(o): return o.arity is Arity.BINARY
    def lau(o): return o.arity is Arity.UNARY and o.associativity is Associativity.LEFT
    def rau(o): return o.arity is Arity.UNARY and o.associativity is Associativity.RIGHT

    # operators that begin/end an expression
    exp_start_ops = [o for o in operators if rau(o)]
    exp_start_ops.extend((LBR, LABS))
    exp_end_ops = [o for o in operators if lau(o)]
    exp_end_ops.extend((RBR, RABS))

    # if there is no token to the left, check fails for binary and left-associative unary operators
    if not left_token and (bin(t) or lau(t)):
        return False

    # if it's a number/constant or the end of an expression, check fails for right-associative unary operators
    # otherwise it fails for all others
    if (isinstance(left_token, Number) or left_token in exp_end_ops) == rau(t):
        return False

    # find the first token to the right
    right_token = _get_token(exp, pos + t_len, t)[0]

    # if there is no token to the right, check fails for binary and right-associative unary operators
    if not right_token and (bin(t) or rau(t)):
        return False

    # if it's a number/constant or the end of an expression, check fails for left-associative unary operators
    # otherwise it fails for all others
    if (isinstance(right_token, Number) or right_token in exp_start_ops) == lau(t):
        return False

    return True


# Replaces |exp| with abs(exp)
def _replace_abs_brackets(tokens):
    i = 0
    while i < len(tokens):
        if tokens[i] is LABS:
            tokens.insert(i, ABS)
            i += 1
            tokens[_find_paired_bracket(tokens, i)] = RBR
            tokens[i] = LBR
        i += 1


def _find_paired_bracket(tokens, pos):
    br = tokens[pos]
    left = LBR, LABS
    right = RBR, RABS
    if br in left:
        p_br = RBR if br is LBR else RABS
        step = 1
    else:
        p_br = LBR if br is RBR else LABS
        step = -1

    depth = 0
    pos += step
    while 0 <= pos < len(tokens):
        if depth < 0:
            return None
        if tokens[pos] is p_br and depth == 0:
            return pos
        if tokens[pos] in left:
            depth += step
        elif tokens[pos] in right:
            depth -= step
        pos += step


def _shunting_yard(tokens):
    queue = []
    stack = []
    for t in tokens:
        if isinstance(t, Number):
            queue.append(t)

        elif isinstance(t, Operator):
            while stack:
                t2 = stack.pop()
                if isinstance(t2, Operator) and (
                    t.associativity is Associativity.LEFT and t.precedence <= t2.precedence or
                    t.associativity is Associativity.RIGHT and t.precedence < t2.precedence
                ):
                    queue.append(t2)
                else:
                    stack.append(t2)
                    break
            stack.append(t)

        elif t is LBR:
            stack.append(t)

        elif t is RBR:
            while stack:
                t2 = stack.pop()
                if t2 is LBR:
                    break
                queue.append(t2)
            else:
                raise ValueError("Mismatched brackets.")

        else:
            raise ValueError("Illegal token: " + str(t))

    while stack:
        t = stack.pop()
        if t in brackets:
            raise ValueError("Mismatched brackets.")
        queue.append(t)

    return queue


def _evaluate(rpn):
    stack = []
    for t in rpn:
        if isinstance(t, Number):
            stack.append(t.value)

        elif isinstance(t, Operator):
            n = 2 if t.arity is Arity.BINARY else 1
            args = []
            for i in range(n):
                if not stack:
                    raise ValueError("Insufficient arguments for operator: " + str(t))
                args.append(stack.pop())
            stack.append(t.f(*(args[::-1])))

        else:
            raise ValueError("Illegal token: " + str(t))

    if len(stack) != 1:
        raise ValueError("Too many values left on stack: " + ", ".join(str(t) for t in stack))

    return stack.pop()


# TESTING

def _get_prec(e):
    for t in e:
        if isinstance(t, Operator):
            o1 = t
    for t in e[::-1]:
        if isinstance(t, Operator):
            o2 = t
    if o2.arity is Arity.BINARY and o1.arity is Arity.UNARY:
        tmp = o1
        o1 = o2
        o2 = tmp
    cmpsign = "<" if o1.precedence < o2.precedence else ">" if o1.precedence > o2.precedence else "="
    return "prec(" + str(o1) + ") " + cmpsign + " prec(" + str(o2) + ")"


print("Case 1: LAB + RAU")
exp = (
    ([Number(5), LAB0, RAU1, Number(1)], "5 1 - +"),
    ([Number(5), LAB1, RAU1, Number(1)], "5 1 - +"),
    ([Number(5), LAB1, RAU0, Number(1)], "5 1 - +"),
    ([RAU1, Number(5), LAB0, Number(1)], "5 - 1 +"),
    ([RAU1, Number(5), LAB1, Number(1)], "5 - 1 +"),
    ([RAU0, Number(5), LAB1, Number(1)], "5 1 + -")
)
for e in exp:
    print(_get_prec(e[0]), end=": ")
    print(" ".join(str(val) for val in e[0]), end=" = ")
    s = " ".join(str(val) for val in _shunting_yard(e[0]))
    print(s + " =/= " + e[1] if s != e[1] else s)
print()

print("Case 2: LAB + LAU")
exp = (
    ([Number(5), LAU1, LAB0, Number(3)], "5 ! 3 +"),
    ([Number(5), LAU1, LAB1, Number(3)], "5 ! 3 +"),
    ([Number(5), LAU0, LAB1, Number(3)], "5 ! 3 +"),
    ([Number(5), LAB0, Number(3), LAU1], "5 3 ! +"),
    ([Number(5), LAB1, Number(3), LAU1], "5 3 + !"),
    ([Number(5), LAB1, Number(3), LAU0], "5 3 + !"),
)
for e in exp:
    print(_get_prec(e[0]), end=": ")
    print(" ".join(str(val) for val in e[0]), end=" = ")
    s = " ".join(str(val) for val in _shunting_yard(e[0]))
    print(s + " =/= " + e[1] if s != e[1] else s)
print()

print("Case 3: RAB + RAU")
exp = (
    ([Number(5), RAB0, RAU1, Number(1)], "5 1 - **"),
    ([Number(5), RAB1, RAU1, Number(1)], "5 1 - **"),
    ([Number(5), RAB1, RAU0, Number(1)], "5 1 - **"),
    ([RAU1, Number(5), RAB0, Number(1)], "5 - 1 **"),
    ([RAU1, Number(5), RAB1, Number(1)], "5 1 ** -"),
    ([RAU0, Number(5), RAB1, Number(1)], "5 1 ** -")
)
for e in exp:
    print(_get_prec(e[0]), end=": ")
    print(" ".join(str(val) for val in e[0]), end=" = ")
    s = " ".join(str(val) for val in _shunting_yard(e[0]))
    print(s + " =/= " + e[1] if s != e[1] else s)
print()

print("Case 4: RAB + LAU")
exp = (
    ([Number(5), LAU1, RAB0, Number(3)], "5 ! 3 **"),
    ([Number(5), LAU1, RAB1, Number(3)], "5 ! 3 **"),
    ([Number(5), LAU0, RAB1, Number(3)], "5 ! 3 **"),
    ([Number(5), RAB0, Number(3), LAU1], "5 3 ! **"),
    ([Number(5), RAB1, Number(3), LAU1], "5 3 ** !"),
    ([Number(5), RAB1, Number(3), LAU0], "5 3 ** !")
)
for e in exp:
    print(_get_prec(e[0]), end=": ")
    print(" ".join(str(val) for val in e[0]), end=" = ")
    s = " ".join(str(val) for val in _shunting_yard(e[0]))
    print(s + " =/= " + e[1] if s != e[1] else s)
print()

print("Case 5: LAU + RAU")
exp = (
    ([RAU0, Number(5), LAU1], "5 ! -"),
    ([RAU1, Number(5), LAU1], "5 - !"),
    ([RAU1, Number(5), LAU0], "5 - !")
)
for e in exp:
    print(_get_prec(e[0]), end=": ")
    print(" ".join(str(val) for val in e[0]), end=" = ")
    s = " ".join(str(val) for val in _shunting_yard(e[0]))
    print(s + " =/= " + e[1] if s != e[1] else s)
print()

print(" ".join(str(val) for val in _shunting_yard([RAU0, Number(5), LAU0, LAB1, Number(3)])))
print(" ".join(str(val) for val in _shunting_yard([RAU0, Number(5), LAU1, LAB0, Number(3)])))
print(" ".join(str(val) for val in _shunting_yard([RAU0, Number(5), LAU1, LAB1, Number(3)])))
print(" ".join(str(val) for val in _shunting_yard([RAU1, Number(5), LAU0, LAB0, Number(3)])))
print(" ".join(str(val) for val in _shunting_yard([RAU1, Number(5), LAU0, LAB1, Number(3)])))
print(" ".join(str(val) for val in _shunting_yard([RAU1, Number(5), LAU1, LAB0, Number(3)])))
print(" ".join(str(val) for val in _shunting_yard([RAU1, Number(5), LAU1, LAB1, Number(3)])))
print()

if __name__ == '__main__':
    main()
