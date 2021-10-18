# rtl2dot

### Usage

```shell
gcc lab.c -O3 -fdump-rtl-all
python3 rtl2dot.py lab.c.229r.expand -o lab.c.229r.dot
# output a .dot file which can be copy to http://magjac.com/graphviz-visual-editor/ to preview
```

lab.c:

```c
int func1(int* a, int* b, int* c, int* d, int* restrict e)
{       
        *a = 100;
        *b = 123;
        int sum = *a + *b + *c + *d;
        if (*e) {
                return *c + *d;
        } else {
                return sum;
        }
}
```
