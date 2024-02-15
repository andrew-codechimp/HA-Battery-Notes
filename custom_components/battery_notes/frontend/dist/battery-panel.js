!function (t) {
  "use strict";

  var e = function (t, r) {
    return e = Object.setPrototypeOf || {
      __proto__: []
    } instanceof Array && function (t, e) {
      t.__proto__ = e;
    } || function (t, e) {
      for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && (t[r] = e[r]);
    }, e(t, r);
  };
  function r(t, r) {
    if ("function" != typeof r && null !== r) throw new TypeError("Class extends value " + String(r) + " is not a constructor or null");
    function i() {
      this.constructor = t;
    }
    e(t, r), t.prototype = null === r ? Object.create(r) : (i.prototype = r.prototype, new i());
  }
  var i = function () {
    return i = Object.assign || function (t) {
      for (var e, r = 1, i = arguments.length; r < i; r++) for (var n in e = arguments[r]) Object.prototype.hasOwnProperty.call(e, n) && (t[n] = e[n]);
      return t;
    }, i.apply(this, arguments);
  };
  function n(t, e, r, i) {
    var n,
      o = arguments.length,
      s = o < 3 ? e : null === i ? i = Object.getOwnPropertyDescriptor(e, r) : i;
    if ("object" == typeof Reflect && "function" == typeof Reflect.decorate) s = Reflect.decorate(t, e, r, i);else for (var a = t.length - 1; a >= 0; a--) (n = t[a]) && (s = (o < 3 ? n(s) : o > 3 ? n(e, r, s) : n(e, r)) || s);
    return o > 3 && s && Object.defineProperty(e, r, s), s;
  }
  function o(t, e, r) {
    if (r || 2 === arguments.length) for (var i, n = 0, o = e.length; n < o; n++) !i && n in e || (i || (i = Array.prototype.slice.call(e, 0, n)), i[n] = e[n]);
    return t.concat(i || Array.prototype.slice.call(e));
  }
  "function" == typeof SuppressedError && SuppressedError;
  /**
       * @license
       * Copyright 2019 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  const s = window,
    a = s.ShadowRoot && (void 0 === s.ShadyCSS || s.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype,
    h = Symbol(),
    l = new WeakMap();
  class c {
    constructor(t, e, r) {
      if (this._$cssResult$ = !0, r !== h) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
      this.cssText = t, this.t = e;
    }
    get styleSheet() {
      let t = this.o;
      const e = this.t;
      if (a && void 0 === t) {
        const r = void 0 !== e && 1 === e.length;
        r && (t = l.get(e)), void 0 === t && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), r && l.set(e, t));
      }
      return t;
    }
    toString() {
      return this.cssText;
    }
  }
  const u = (t, ...e) => {
      const r = 1 === t.length ? t[0] : e.reduce((e, r, i) => e + (t => {
        if (!0 === t._$cssResult$) return t.cssText;
        if ("number" == typeof t) return t;
        throw Error("Value passed to 'css' function must be a 'css' function result: " + t + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
      })(r) + t[i + 1], t[0]);
      return new c(r, t, h);
    },
    p = a ? t => t : t => t instanceof CSSStyleSheet ? (t => {
      let e = "";
      for (const r of t.cssRules) e += r.cssText;
      return (t => new c("string" == typeof t ? t : t + "", void 0, h))(e);
    })(t) : t
    /**
         * @license
         * Copyright 2017 Google LLC
         * SPDX-License-Identifier: BSD-3-Clause
         */;
  var d;
  const f = window,
    m = f.trustedTypes,
    g = m ? m.emptyScript : "",
    v = f.reactiveElementPolyfillSupport,
    E = {
      toAttribute(t, e) {
        switch (e) {
          case Boolean:
            t = t ? g : null;
            break;
          case Object:
          case Array:
            t = null == t ? t : JSON.stringify(t);
        }
        return t;
      },
      fromAttribute(t, e) {
        let r = t;
        switch (e) {
          case Boolean:
            r = null !== t;
            break;
          case Number:
            r = null === t ? null : Number(t);
            break;
          case Object:
          case Array:
            try {
              r = JSON.parse(t);
            } catch (t) {
              r = null;
            }
        }
        return r;
      }
    },
    b = (t, e) => e !== t && (e == e || t == t),
    y = {
      attribute: !0,
      type: String,
      converter: E,
      reflect: !1,
      hasChanged: b
    },
    _ = "finalized";
  class A extends HTMLElement {
    constructor() {
      super(), this._$Ei = new Map(), this.isUpdatePending = !1, this.hasUpdated = !1, this._$El = null, this._$Eu();
    }
    static addInitializer(t) {
      var e;
      this.finalize(), (null !== (e = this.h) && void 0 !== e ? e : this.h = []).push(t);
    }
    static get observedAttributes() {
      this.finalize();
      const t = [];
      return this.elementProperties.forEach((e, r) => {
        const i = this._$Ep(r, e);
        void 0 !== i && (this._$Ev.set(i, r), t.push(i));
      }), t;
    }
    static createProperty(t, e = y) {
      if (e.state && (e.attribute = !1), this.finalize(), this.elementProperties.set(t, e), !e.noAccessor && !this.prototype.hasOwnProperty(t)) {
        const r = "symbol" == typeof t ? Symbol() : "__" + t,
          i = this.getPropertyDescriptor(t, r, e);
        void 0 !== i && Object.defineProperty(this.prototype, t, i);
      }
    }
    static getPropertyDescriptor(t, e, r) {
      return {
        get() {
          return this[e];
        },
        set(i) {
          const n = this[t];
          this[e] = i, this.requestUpdate(t, n, r);
        },
        configurable: !0,
        enumerable: !0
      };
    }
    static getPropertyOptions(t) {
      return this.elementProperties.get(t) || y;
    }
    static finalize() {
      if (this.hasOwnProperty(_)) return !1;
      this[_] = !0;
      const t = Object.getPrototypeOf(this);
      if (t.finalize(), void 0 !== t.h && (this.h = [...t.h]), this.elementProperties = new Map(t.elementProperties), this._$Ev = new Map(), this.hasOwnProperty("properties")) {
        const t = this.properties,
          e = [...Object.getOwnPropertyNames(t), ...Object.getOwnPropertySymbols(t)];
        for (const r of e) this.createProperty(r, t[r]);
      }
      return this.elementStyles = this.finalizeStyles(this.styles), !0;
    }
    static finalizeStyles(t) {
      const e = [];
      if (Array.isArray(t)) {
        const r = new Set(t.flat(1 / 0).reverse());
        for (const t of r) e.unshift(p(t));
      } else void 0 !== t && e.push(p(t));
      return e;
    }
    static _$Ep(t, e) {
      const r = e.attribute;
      return !1 === r ? void 0 : "string" == typeof r ? r : "string" == typeof t ? t.toLowerCase() : void 0;
    }
    _$Eu() {
      var t;
      this._$E_ = new Promise(t => this.enableUpdating = t), this._$AL = new Map(), this._$Eg(), this.requestUpdate(), null === (t = this.constructor.h) || void 0 === t || t.forEach(t => t(this));
    }
    addController(t) {
      var e, r;
      (null !== (e = this._$ES) && void 0 !== e ? e : this._$ES = []).push(t), void 0 !== this.renderRoot && this.isConnected && (null === (r = t.hostConnected) || void 0 === r || r.call(t));
    }
    removeController(t) {
      var e;
      null === (e = this._$ES) || void 0 === e || e.splice(this._$ES.indexOf(t) >>> 0, 1);
    }
    _$Eg() {
      this.constructor.elementProperties.forEach((t, e) => {
        this.hasOwnProperty(e) && (this._$Ei.set(e, this[e]), delete this[e]);
      });
    }
    createRenderRoot() {
      var t;
      const e = null !== (t = this.shadowRoot) && void 0 !== t ? t : this.attachShadow(this.constructor.shadowRootOptions);
      return ((t, e) => {
        a ? t.adoptedStyleSheets = e.map(t => t instanceof CSSStyleSheet ? t : t.styleSheet) : e.forEach(e => {
          const r = document.createElement("style"),
            i = s.litNonce;
          void 0 !== i && r.setAttribute("nonce", i), r.textContent = e.cssText, t.appendChild(r);
        });
      })(e, this.constructor.elementStyles), e;
    }
    connectedCallback() {
      var t;
      void 0 === this.renderRoot && (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), null === (t = this._$ES) || void 0 === t || t.forEach(t => {
        var e;
        return null === (e = t.hostConnected) || void 0 === e ? void 0 : e.call(t);
      });
    }
    enableUpdating(t) {}
    disconnectedCallback() {
      var t;
      null === (t = this._$ES) || void 0 === t || t.forEach(t => {
        var e;
        return null === (e = t.hostDisconnected) || void 0 === e ? void 0 : e.call(t);
      });
    }
    attributeChangedCallback(t, e, r) {
      this._$AK(t, r);
    }
    _$EO(t, e, r = y) {
      var i;
      const n = this.constructor._$Ep(t, r);
      if (void 0 !== n && !0 === r.reflect) {
        const o = (void 0 !== (null === (i = r.converter) || void 0 === i ? void 0 : i.toAttribute) ? r.converter : E).toAttribute(e, r.type);
        this._$El = t, null == o ? this.removeAttribute(n) : this.setAttribute(n, o), this._$El = null;
      }
    }
    _$AK(t, e) {
      var r;
      const i = this.constructor,
        n = i._$Ev.get(t);
      if (void 0 !== n && this._$El !== n) {
        const t = i.getPropertyOptions(n),
          o = "function" == typeof t.converter ? {
            fromAttribute: t.converter
          } : void 0 !== (null === (r = t.converter) || void 0 === r ? void 0 : r.fromAttribute) ? t.converter : E;
        this._$El = n, this[n] = o.fromAttribute(e, t.type), this._$El = null;
      }
    }
    requestUpdate(t, e, r) {
      let i = !0;
      void 0 !== t && (((r = r || this.constructor.getPropertyOptions(t)).hasChanged || b)(this[t], e) ? (this._$AL.has(t) || this._$AL.set(t, e), !0 === r.reflect && this._$El !== t && (void 0 === this._$EC && (this._$EC = new Map()), this._$EC.set(t, r))) : i = !1), !this.isUpdatePending && i && (this._$E_ = this._$Ej());
    }
    async _$Ej() {
      this.isUpdatePending = !0;
      try {
        await this._$E_;
      } catch (t) {
        Promise.reject(t);
      }
      const t = this.scheduleUpdate();
      return null != t && (await t), !this.isUpdatePending;
    }
    scheduleUpdate() {
      return this.performUpdate();
    }
    performUpdate() {
      var t;
      if (!this.isUpdatePending) return;
      this.hasUpdated, this._$Ei && (this._$Ei.forEach((t, e) => this[e] = t), this._$Ei = void 0);
      let e = !1;
      const r = this._$AL;
      try {
        e = this.shouldUpdate(r), e ? (this.willUpdate(r), null === (t = this._$ES) || void 0 === t || t.forEach(t => {
          var e;
          return null === (e = t.hostUpdate) || void 0 === e ? void 0 : e.call(t);
        }), this.update(r)) : this._$Ek();
      } catch (t) {
        throw e = !1, this._$Ek(), t;
      }
      e && this._$AE(r);
    }
    willUpdate(t) {}
    _$AE(t) {
      var e;
      null === (e = this._$ES) || void 0 === e || e.forEach(t => {
        var e;
        return null === (e = t.hostUpdated) || void 0 === e ? void 0 : e.call(t);
      }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(t)), this.updated(t);
    }
    _$Ek() {
      this._$AL = new Map(), this.isUpdatePending = !1;
    }
    get updateComplete() {
      return this.getUpdateComplete();
    }
    getUpdateComplete() {
      return this._$E_;
    }
    shouldUpdate(t) {
      return !0;
    }
    update(t) {
      void 0 !== this._$EC && (this._$EC.forEach((t, e) => this._$EO(e, this[e], t)), this._$EC = void 0), this._$Ek();
    }
    updated(t) {}
    firstUpdated(t) {}
  }
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  var H;
  A[_] = !0, A.elementProperties = new Map(), A.elementStyles = [], A.shadowRootOptions = {
    mode: "open"
  }, null == v || v({
    ReactiveElement: A
  }), (null !== (d = f.reactiveElementVersions) && void 0 !== d ? d : f.reactiveElementVersions = []).push("1.6.3");
  const T = window,
    B = T.trustedTypes,
    S = B ? B.createPolicy("lit-html", {
      createHTML: t => t
    }) : void 0,
    P = "$lit$",
    w = `lit$${(Math.random() + "").slice(9)}$`,
    C = "?" + w,
    N = `<${C}>`,
    L = document,
    $ = () => L.createComment(""),
    R = t => null === t || "object" != typeof t && "function" != typeof t,
    I = Array.isArray,
    O = "[ \t\n\f\r]",
    U = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,
    M = /-->/g,
    x = />/g,
    G = RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"),
    D = /'/g,
    k = /"/g,
    F = /^(?:script|style|textarea|title)$/i,
    V = (t => (e, ...r) => ({
      _$litType$: t,
      strings: e,
      values: r
    }))(1),
    j = Symbol.for("lit-noChange"),
    X = Symbol.for("lit-nothing"),
    K = new WeakMap(),
    z = L.createTreeWalker(L, 129, null, !1);
  function Y(t, e) {
    if (!Array.isArray(t) || !t.hasOwnProperty("raw")) throw Error("invalid template strings array");
    return void 0 !== S ? S.createHTML(e) : e;
  }
  const W = (t, e) => {
    const r = t.length - 1,
      i = [];
    let n,
      o = 2 === e ? "<svg>" : "",
      s = U;
    for (let e = 0; e < r; e++) {
      const r = t[e];
      let a,
        h,
        l = -1,
        c = 0;
      for (; c < r.length && (s.lastIndex = c, h = s.exec(r), null !== h);) c = s.lastIndex, s === U ? "!--" === h[1] ? s = M : void 0 !== h[1] ? s = x : void 0 !== h[2] ? (F.test(h[2]) && (n = RegExp("</" + h[2], "g")), s = G) : void 0 !== h[3] && (s = G) : s === G ? ">" === h[0] ? (s = null != n ? n : U, l = -1) : void 0 === h[1] ? l = -2 : (l = s.lastIndex - h[2].length, a = h[1], s = void 0 === h[3] ? G : '"' === h[3] ? k : D) : s === k || s === D ? s = G : s === M || s === x ? s = U : (s = G, n = void 0);
      const u = s === G && t[e + 1].startsWith("/>") ? " " : "";
      o += s === U ? r + N : l >= 0 ? (i.push(a), r.slice(0, l) + P + r.slice(l) + w + u) : r + w + (-2 === l ? (i.push(void 0), e) : u);
    }
    return [Y(t, o + (t[r] || "<?>") + (2 === e ? "</svg>" : "")), i];
  };
  class Z {
    constructor({
      strings: t,
      _$litType$: e
    }, r) {
      let i;
      this.parts = [];
      let n = 0,
        o = 0;
      const s = t.length - 1,
        a = this.parts,
        [h, l] = W(t, e);
      if (this.el = Z.createElement(h, r), z.currentNode = this.el.content, 2 === e) {
        const t = this.el.content,
          e = t.firstChild;
        e.remove(), t.append(...e.childNodes);
      }
      for (; null !== (i = z.nextNode()) && a.length < s;) {
        if (1 === i.nodeType) {
          if (i.hasAttributes()) {
            const t = [];
            for (const e of i.getAttributeNames()) if (e.endsWith(P) || e.startsWith(w)) {
              const r = l[o++];
              if (t.push(e), void 0 !== r) {
                const t = i.getAttribute(r.toLowerCase() + P).split(w),
                  e = /([.?@])?(.*)/.exec(r);
                a.push({
                  type: 1,
                  index: n,
                  name: e[2],
                  strings: t,
                  ctor: "." === e[1] ? et : "?" === e[1] ? it : "@" === e[1] ? nt : tt
                });
              } else a.push({
                type: 6,
                index: n
              });
            }
            for (const e of t) i.removeAttribute(e);
          }
          if (F.test(i.tagName)) {
            const t = i.textContent.split(w),
              e = t.length - 1;
            if (e > 0) {
              i.textContent = B ? B.emptyScript : "";
              for (let r = 0; r < e; r++) i.append(t[r], $()), z.nextNode(), a.push({
                type: 2,
                index: ++n
              });
              i.append(t[e], $());
            }
          }
        } else if (8 === i.nodeType) if (i.data === C) a.push({
          type: 2,
          index: n
        });else {
          let t = -1;
          for (; -1 !== (t = i.data.indexOf(w, t + 1));) a.push({
            type: 7,
            index: n
          }), t += w.length - 1;
        }
        n++;
      }
    }
    static createElement(t, e) {
      const r = L.createElement("template");
      return r.innerHTML = t, r;
    }
  }
  function q(t, e, r = t, i) {
    var n, o, s, a;
    if (e === j) return e;
    let h = void 0 !== i ? null === (n = r._$Co) || void 0 === n ? void 0 : n[i] : r._$Cl;
    const l = R(e) ? void 0 : e._$litDirective$;
    return (null == h ? void 0 : h.constructor) !== l && (null === (o = null == h ? void 0 : h._$AO) || void 0 === o || o.call(h, !1), void 0 === l ? h = void 0 : (h = new l(t), h._$AT(t, r, i)), void 0 !== i ? (null !== (s = (a = r)._$Co) && void 0 !== s ? s : a._$Co = [])[i] = h : r._$Cl = h), void 0 !== h && (e = q(t, h._$AS(t, e.values), h, i)), e;
  }
  class J {
    constructor(t, e) {
      this._$AV = [], this._$AN = void 0, this._$AD = t, this._$AM = e;
    }
    get parentNode() {
      return this._$AM.parentNode;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    u(t) {
      var e;
      const {
          el: {
            content: r
          },
          parts: i
        } = this._$AD,
        n = (null !== (e = null == t ? void 0 : t.creationScope) && void 0 !== e ? e : L).importNode(r, !0);
      z.currentNode = n;
      let o = z.nextNode(),
        s = 0,
        a = 0,
        h = i[0];
      for (; void 0 !== h;) {
        if (s === h.index) {
          let e;
          2 === h.type ? e = new Q(o, o.nextSibling, this, t) : 1 === h.type ? e = new h.ctor(o, h.name, h.strings, this, t) : 6 === h.type && (e = new ot(o, this, t)), this._$AV.push(e), h = i[++a];
        }
        s !== (null == h ? void 0 : h.index) && (o = z.nextNode(), s++);
      }
      return z.currentNode = L, n;
    }
    v(t) {
      let e = 0;
      for (const r of this._$AV) void 0 !== r && (void 0 !== r.strings ? (r._$AI(t, r, e), e += r.strings.length - 2) : r._$AI(t[e])), e++;
    }
  }
  class Q {
    constructor(t, e, r, i) {
      var n;
      this.type = 2, this._$AH = X, this._$AN = void 0, this._$AA = t, this._$AB = e, this._$AM = r, this.options = i, this._$Cp = null === (n = null == i ? void 0 : i.isConnected) || void 0 === n || n;
    }
    get _$AU() {
      var t, e;
      return null !== (e = null === (t = this._$AM) || void 0 === t ? void 0 : t._$AU) && void 0 !== e ? e : this._$Cp;
    }
    get parentNode() {
      let t = this._$AA.parentNode;
      const e = this._$AM;
      return void 0 !== e && 11 === (null == t ? void 0 : t.nodeType) && (t = e.parentNode), t;
    }
    get startNode() {
      return this._$AA;
    }
    get endNode() {
      return this._$AB;
    }
    _$AI(t, e = this) {
      t = q(this, t, e), R(t) ? t === X || null == t || "" === t ? (this._$AH !== X && this._$AR(), this._$AH = X) : t !== this._$AH && t !== j && this._(t) : void 0 !== t._$litType$ ? this.g(t) : void 0 !== t.nodeType ? this.$(t) : (t => I(t) || "function" == typeof (null == t ? void 0 : t[Symbol.iterator]))(t) ? this.T(t) : this._(t);
    }
    k(t) {
      return this._$AA.parentNode.insertBefore(t, this._$AB);
    }
    $(t) {
      this._$AH !== t && (this._$AR(), this._$AH = this.k(t));
    }
    _(t) {
      this._$AH !== X && R(this._$AH) ? this._$AA.nextSibling.data = t : this.$(L.createTextNode(t)), this._$AH = t;
    }
    g(t) {
      var e;
      const {
          values: r,
          _$litType$: i
        } = t,
        n = "number" == typeof i ? this._$AC(t) : (void 0 === i.el && (i.el = Z.createElement(Y(i.h, i.h[0]), this.options)), i);
      if ((null === (e = this._$AH) || void 0 === e ? void 0 : e._$AD) === n) this._$AH.v(r);else {
        const t = new J(n, this),
          e = t.u(this.options);
        t.v(r), this.$(e), this._$AH = t;
      }
    }
    _$AC(t) {
      let e = K.get(t.strings);
      return void 0 === e && K.set(t.strings, e = new Z(t)), e;
    }
    T(t) {
      I(this._$AH) || (this._$AH = [], this._$AR());
      const e = this._$AH;
      let r,
        i = 0;
      for (const n of t) i === e.length ? e.push(r = new Q(this.k($()), this.k($()), this, this.options)) : r = e[i], r._$AI(n), i++;
      i < e.length && (this._$AR(r && r._$AB.nextSibling, i), e.length = i);
    }
    _$AR(t = this._$AA.nextSibling, e) {
      var r;
      for (null === (r = this._$AP) || void 0 === r || r.call(this, !1, !0, e); t && t !== this._$AB;) {
        const e = t.nextSibling;
        t.remove(), t = e;
      }
    }
    setConnected(t) {
      var e;
      void 0 === this._$AM && (this._$Cp = t, null === (e = this._$AP) || void 0 === e || e.call(this, t));
    }
  }
  class tt {
    constructor(t, e, r, i, n) {
      this.type = 1, this._$AH = X, this._$AN = void 0, this.element = t, this.name = e, this._$AM = i, this.options = n, r.length > 2 || "" !== r[0] || "" !== r[1] ? (this._$AH = Array(r.length - 1).fill(new String()), this.strings = r) : this._$AH = X;
    }
    get tagName() {
      return this.element.tagName;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(t, e = this, r, i) {
      const n = this.strings;
      let o = !1;
      if (void 0 === n) t = q(this, t, e, 0), o = !R(t) || t !== this._$AH && t !== j, o && (this._$AH = t);else {
        const i = t;
        let s, a;
        for (t = n[0], s = 0; s < n.length - 1; s++) a = q(this, i[r + s], e, s), a === j && (a = this._$AH[s]), o || (o = !R(a) || a !== this._$AH[s]), a === X ? t = X : t !== X && (t += (null != a ? a : "") + n[s + 1]), this._$AH[s] = a;
      }
      o && !i && this.j(t);
    }
    j(t) {
      t === X ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, null != t ? t : "");
    }
  }
  class et extends tt {
    constructor() {
      super(...arguments), this.type = 3;
    }
    j(t) {
      this.element[this.name] = t === X ? void 0 : t;
    }
  }
  const rt = B ? B.emptyScript : "";
  class it extends tt {
    constructor() {
      super(...arguments), this.type = 4;
    }
    j(t) {
      t && t !== X ? this.element.setAttribute(this.name, rt) : this.element.removeAttribute(this.name);
    }
  }
  class nt extends tt {
    constructor(t, e, r, i, n) {
      super(t, e, r, i, n), this.type = 5;
    }
    _$AI(t, e = this) {
      var r;
      if ((t = null !== (r = q(this, t, e, 0)) && void 0 !== r ? r : X) === j) return;
      const i = this._$AH,
        n = t === X && i !== X || t.capture !== i.capture || t.once !== i.once || t.passive !== i.passive,
        o = t !== X && (i === X || n);
      n && this.element.removeEventListener(this.name, this, i), o && this.element.addEventListener(this.name, this, t), this._$AH = t;
    }
    handleEvent(t) {
      var e, r;
      "function" == typeof this._$AH ? this._$AH.call(null !== (r = null === (e = this.options) || void 0 === e ? void 0 : e.host) && void 0 !== r ? r : this.element, t) : this._$AH.handleEvent(t);
    }
  }
  class ot {
    constructor(t, e, r) {
      this.element = t, this.type = 6, this._$AN = void 0, this._$AM = e, this.options = r;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(t) {
      q(this, t);
    }
  }
  const st = T.litHtmlPolyfillSupport;
  null == st || st(Z, Q), (null !== (H = T.litHtmlVersions) && void 0 !== H ? H : T.litHtmlVersions = []).push("2.8.0");
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  var at, ht;
  class lt extends A {
    constructor() {
      super(...arguments), this.renderOptions = {
        host: this
      }, this._$Do = void 0;
    }
    createRenderRoot() {
      var t, e;
      const r = super.createRenderRoot();
      return null !== (t = (e = this.renderOptions).renderBefore) && void 0 !== t || (e.renderBefore = r.firstChild), r;
    }
    update(t) {
      const e = this.render();
      this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = ((t, e, r) => {
        var i, n;
        const o = null !== (i = null == r ? void 0 : r.renderBefore) && void 0 !== i ? i : e;
        let s = o._$litPart$;
        if (void 0 === s) {
          const t = null !== (n = null == r ? void 0 : r.renderBefore) && void 0 !== n ? n : null;
          o._$litPart$ = s = new Q(e.insertBefore($(), t), t, void 0, null != r ? r : {});
        }
        return s._$AI(t), s;
      })(e, this.renderRoot, this.renderOptions);
    }
    connectedCallback() {
      var t;
      super.connectedCallback(), null === (t = this._$Do) || void 0 === t || t.setConnected(!0);
    }
    disconnectedCallback() {
      var t;
      super.disconnectedCallback(), null === (t = this._$Do) || void 0 === t || t.setConnected(!1);
    }
    render() {
      return j;
    }
  }
  lt.finalized = !0, lt._$litElement$ = !0, null === (at = globalThis.litElementHydrateSupport) || void 0 === at || at.call(globalThis, {
    LitElement: lt
  });
  const ct = globalThis.litElementPolyfillSupport;
  null == ct || ct({
    LitElement: lt
  }), (null !== (ht = globalThis.litElementVersions) && void 0 !== ht ? ht : globalThis.litElementVersions = []).push("3.3.3");
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  const ut = (t, e) => "method" === e.kind && e.descriptor && !("value" in e.descriptor) ? {
    ...e,
    finisher(r) {
      r.createProperty(e.key, t);
    }
  } : {
    kind: "field",
    key: Symbol(),
    placement: "own",
    descriptor: {},
    originalKey: e.key,
    initializer() {
      "function" == typeof e.initializer && (this[e.key] = e.initializer.call(this));
    },
    finisher(r) {
      r.createProperty(e.key, t);
    }
  };
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  function pt(t) {
    return (e, r) => void 0 !== r ? ((t, e, r) => {
      e.constructor.createProperty(r, t);
    })(t, e, r) : ut(t, e);
    /**
         * @license
         * Copyright 2021 Google LLC
         * SPDX-License-Identifier: BSD-3-Clause
         */
  }
  var dt;
  null === (dt = window.HTMLSlotElement) || void 0 === dt || dt.prototype.assignedElements;
  const ft = u`
  ha-card {
    display: flex;
    flex-direction: column;
    margin: 5px;
    max-width: calc(100vw - 10px);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
  }
  .card-header .name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  div.warning {
    color: var(--error-color);
    margin-top: 20px;
  }

  div.checkbox-row {
    min-height: 40px;
    display: flex;
    align-items: center;
  }

  div.checkbox-row ha-switch {
    margin-right: 20px;
  }

  div.checkbox-row.right ha-switch {
    margin-left: 20px;
    position: absolute;
    right: 0px;
  }

  mwc-button.active:not([disabled]) {
    background: var(--primary-color);
    --mdc-theme-primary: var(--text-primary-color);
    border-radius: 4px;
  }
  mwc-button.warning {
    --mdc-theme-primary: var(--error-color);
  }
  mwc-button.success {
    --mdc-theme-primary: var(--success-color);
  }

  div.entity-row {
    display: flex;
    align-items: center;
    flex-direction: row;
    margin: 10px 0px;
  }
  div.entity-row .info {
    margin-left: 16px;
    flex: 1 0 60px;
  }
  div.entity-row .info,
  div.entity-row .info > * {
    color: var(--primary-text-color);
    transition: color 0.2s ease-in-out;
  }
  div.entity-row .secondary {
    display: block;
    color: var(--secondary-text-color);
    transition: color 0.2s ease-in-out;
  }
  div.entity-row state-badge {
    flex: 0 0 40px;
  }

  ha-dialog div.wrapper {
    margin-bottom: -20px;
  }

  ha-textfield {
    min-width: 220px;
  }

  a,
  a:visited {
    color: var(--primary-color);
  }
  mwc-button ha-icon {
    padding-right: 11px;
  }
  mwc-button[trailingIcon] ha-icon {
    padding: 0px 0px 0px 6px;
  }
  mwc-button.vertical {
    height: 60px;
    --mdc-button-height: 60px;
    background: var(--primary-color);
    --mdc-theme-primary: var(--text-primary-color);
  }
  mwc-button.vertical div {
    display: flex;
    flex-direction: column;
  }
  mwc-button.vertical span {
    display: flex;
  }
  mwc-button.vertical ha-icon {
    display: flex;
    margin-left: 50%;
  }
  mwc-tab {
    --mdc-tab-color-default: var(--secondary-text-color);
    --mdc-tab-text-label-color-default: var(--secondary-text-color);
  }
  mwc-tab ha-icon {
    --mdc-icon-size: 20px;
  }
  mwc-tab.disabled {
    --mdc-theme-primary: var(--disabled-text-color);
    --mdc-tab-color-default: var(--disabled-text-color);
    --mdc-tab-text-label-color-default: var(--disabled-text-color);
  }

  ha-card settings-row:first-child,
  ha-card settings-row:first-of-type {
    border-top: 0px;
  }

  ha-card > ha-card {
    margin: 10px;
  }
`;
  u`
  /* mwc-dialog (ha-dialog) styles */
  ha-dialog {
    --mdc-dialog-min-width: 400px;
    --mdc-dialog-max-width: 600px;
    --mdc-dialog-heading-ink-color: var(--primary-text-color);
    --mdc-dialog-content-ink-color: var(--primary-text-color);
    --justify-action-buttons: space-between;
  }
  /* make dialog fullscreen on small screens */
  @media all and (max-width: 450px), all and (max-height: 500px) {
    ha-dialog {
      --mdc-dialog-min-width: calc(100vw - env(safe-area-inset-right) - env(safe-area-inset-left));
      --mdc-dialog-max-width: calc(100vw - env(safe-area-inset-right) - env(safe-area-inset-left));
      --mdc-dialog-min-height: 100%;
      --mdc-dialog-max-height: 100%;
      --vertial-align-dialog: flex-end;
      --ha-dialog-border-radius: 0px;
    }
  }
  ha-dialog div.description {
    margin-bottom: 10px;
  }
`;
  var mt,
    gt,
    vt,
    Et = "Battery Notes",
    bt = {
      documentation: "Documentation"
    },
    yt = {
      title: Et,
      menu: bt
    },
    _t = Object.freeze({
      __proto__: null,
      title: Et,
      menu: bt,
      default: yt
    });
  function At(t) {
    return t.type === gt.literal;
  }
  function Ht(t) {
    return t.type === gt.argument;
  }
  function Tt(t) {
    return t.type === gt.number;
  }
  function Bt(t) {
    return t.type === gt.date;
  }
  function St(t) {
    return t.type === gt.time;
  }
  function Pt(t) {
    return t.type === gt.select;
  }
  function wt(t) {
    return t.type === gt.plural;
  }
  function Ct(t) {
    return t.type === gt.pound;
  }
  function Nt(t) {
    return t.type === gt.tag;
  }
  function Lt(t) {
    return !(!t || "object" != typeof t || t.type !== vt.number);
  }
  function $t(t) {
    return !(!t || "object" != typeof t || t.type !== vt.dateTime);
  }
  !function (t) {
    t[t.EXPECT_ARGUMENT_CLOSING_BRACE = 1] = "EXPECT_ARGUMENT_CLOSING_BRACE", t[t.EMPTY_ARGUMENT = 2] = "EMPTY_ARGUMENT", t[t.MALFORMED_ARGUMENT = 3] = "MALFORMED_ARGUMENT", t[t.EXPECT_ARGUMENT_TYPE = 4] = "EXPECT_ARGUMENT_TYPE", t[t.INVALID_ARGUMENT_TYPE = 5] = "INVALID_ARGUMENT_TYPE", t[t.EXPECT_ARGUMENT_STYLE = 6] = "EXPECT_ARGUMENT_STYLE", t[t.INVALID_NUMBER_SKELETON = 7] = "INVALID_NUMBER_SKELETON", t[t.INVALID_DATE_TIME_SKELETON = 8] = "INVALID_DATE_TIME_SKELETON", t[t.EXPECT_NUMBER_SKELETON = 9] = "EXPECT_NUMBER_SKELETON", t[t.EXPECT_DATE_TIME_SKELETON = 10] = "EXPECT_DATE_TIME_SKELETON", t[t.UNCLOSED_QUOTE_IN_ARGUMENT_STYLE = 11] = "UNCLOSED_QUOTE_IN_ARGUMENT_STYLE", t[t.EXPECT_SELECT_ARGUMENT_OPTIONS = 12] = "EXPECT_SELECT_ARGUMENT_OPTIONS", t[t.EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE = 13] = "EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE", t[t.INVALID_PLURAL_ARGUMENT_OFFSET_VALUE = 14] = "INVALID_PLURAL_ARGUMENT_OFFSET_VALUE", t[t.EXPECT_SELECT_ARGUMENT_SELECTOR = 15] = "EXPECT_SELECT_ARGUMENT_SELECTOR", t[t.EXPECT_PLURAL_ARGUMENT_SELECTOR = 16] = "EXPECT_PLURAL_ARGUMENT_SELECTOR", t[t.EXPECT_SELECT_ARGUMENT_SELECTOR_FRAGMENT = 17] = "EXPECT_SELECT_ARGUMENT_SELECTOR_FRAGMENT", t[t.EXPECT_PLURAL_ARGUMENT_SELECTOR_FRAGMENT = 18] = "EXPECT_PLURAL_ARGUMENT_SELECTOR_FRAGMENT", t[t.INVALID_PLURAL_ARGUMENT_SELECTOR = 19] = "INVALID_PLURAL_ARGUMENT_SELECTOR", t[t.DUPLICATE_PLURAL_ARGUMENT_SELECTOR = 20] = "DUPLICATE_PLURAL_ARGUMENT_SELECTOR", t[t.DUPLICATE_SELECT_ARGUMENT_SELECTOR = 21] = "DUPLICATE_SELECT_ARGUMENT_SELECTOR", t[t.MISSING_OTHER_CLAUSE = 22] = "MISSING_OTHER_CLAUSE", t[t.INVALID_TAG = 23] = "INVALID_TAG", t[t.INVALID_TAG_NAME = 25] = "INVALID_TAG_NAME", t[t.UNMATCHED_CLOSING_TAG = 26] = "UNMATCHED_CLOSING_TAG", t[t.UNCLOSED_TAG = 27] = "UNCLOSED_TAG";
  }(mt || (mt = {})), function (t) {
    t[t.literal = 0] = "literal", t[t.argument = 1] = "argument", t[t.number = 2] = "number", t[t.date = 3] = "date", t[t.time = 4] = "time", t[t.select = 5] = "select", t[t.plural = 6] = "plural", t[t.pound = 7] = "pound", t[t.tag = 8] = "tag";
  }(gt || (gt = {})), function (t) {
    t[t.number = 0] = "number", t[t.dateTime = 1] = "dateTime";
  }(vt || (vt = {}));
  var Rt = /[ \xA0\u1680\u2000-\u200A\u202F\u205F\u3000]/,
    It = /(?:[Eec]{1,6}|G{1,5}|[Qq]{1,5}|(?:[yYur]+|U{1,5})|[ML]{1,5}|d{1,2}|D{1,3}|F{1}|[abB]{1,5}|[hkHK]{1,2}|w{1,2}|W{1}|m{1,2}|s{1,2}|[zZOvVxX]{1,4})(?=([^']*'[^']*')*[^']*$)/g;
  function Ot(t) {
    var e = {};
    return t.replace(It, function (t) {
      var r = t.length;
      switch (t[0]) {
        case "G":
          e.era = 4 === r ? "long" : 5 === r ? "narrow" : "short";
          break;
        case "y":
          e.year = 2 === r ? "2-digit" : "numeric";
          break;
        case "Y":
        case "u":
        case "U":
        case "r":
          throw new RangeError("`Y/u/U/r` (year) patterns are not supported, use `y` instead");
        case "q":
        case "Q":
          throw new RangeError("`q/Q` (quarter) patterns are not supported");
        case "M":
        case "L":
          e.month = ["numeric", "2-digit", "short", "long", "narrow"][r - 1];
          break;
        case "w":
        case "W":
          throw new RangeError("`w/W` (week) patterns are not supported");
        case "d":
          e.day = ["numeric", "2-digit"][r - 1];
          break;
        case "D":
        case "F":
        case "g":
          throw new RangeError("`D/F/g` (day) patterns are not supported, use `d` instead");
        case "E":
          e.weekday = 4 === r ? "long" : 5 === r ? "narrow" : "short";
          break;
        case "e":
          if (r < 4) throw new RangeError("`e..eee` (weekday) patterns are not supported");
          e.weekday = ["short", "long", "narrow", "short"][r - 4];
          break;
        case "c":
          if (r < 4) throw new RangeError("`c..ccc` (weekday) patterns are not supported");
          e.weekday = ["short", "long", "narrow", "short"][r - 4];
          break;
        case "a":
          e.hour12 = !0;
          break;
        case "b":
        case "B":
          throw new RangeError("`b/B` (period) patterns are not supported, use `a` instead");
        case "h":
          e.hourCycle = "h12", e.hour = ["numeric", "2-digit"][r - 1];
          break;
        case "H":
          e.hourCycle = "h23", e.hour = ["numeric", "2-digit"][r - 1];
          break;
        case "K":
          e.hourCycle = "h11", e.hour = ["numeric", "2-digit"][r - 1];
          break;
        case "k":
          e.hourCycle = "h24", e.hour = ["numeric", "2-digit"][r - 1];
          break;
        case "j":
        case "J":
        case "C":
          throw new RangeError("`j/J/C` (hour) patterns are not supported, use `h/H/K/k` instead");
        case "m":
          e.minute = ["numeric", "2-digit"][r - 1];
          break;
        case "s":
          e.second = ["numeric", "2-digit"][r - 1];
          break;
        case "S":
        case "A":
          throw new RangeError("`S/A` (second) patterns are not supported, use `s` instead");
        case "z":
          e.timeZoneName = r < 4 ? "short" : "long";
          break;
        case "Z":
        case "O":
        case "v":
        case "V":
        case "X":
        case "x":
          throw new RangeError("`Z/O/v/V/X/x` (timeZone) patterns are not supported, use `z` instead");
      }
      return "";
    }), e;
  }
  var Ut = /[\t-\r \x85\u200E\u200F\u2028\u2029]/i;
  var Mt = /^\.(?:(0+)(\*)?|(#+)|(0+)(#+))$/g,
    xt = /^(@+)?(\+|#+)?[rs]?$/g,
    Gt = /(\*)(0+)|(#+)(0+)|(0+)/g,
    Dt = /^(0+)$/;
  function kt(t) {
    var e = {};
    return "r" === t[t.length - 1] ? e.roundingPriority = "morePrecision" : "s" === t[t.length - 1] && (e.roundingPriority = "lessPrecision"), t.replace(xt, function (t, r, i) {
      return "string" != typeof i ? (e.minimumSignificantDigits = r.length, e.maximumSignificantDigits = r.length) : "+" === i ? e.minimumSignificantDigits = r.length : "#" === r[0] ? e.maximumSignificantDigits = r.length : (e.minimumSignificantDigits = r.length, e.maximumSignificantDigits = r.length + ("string" == typeof i ? i.length : 0)), "";
    }), e;
  }
  function Ft(t) {
    switch (t) {
      case "sign-auto":
        return {
          signDisplay: "auto"
        };
      case "sign-accounting":
      case "()":
        return {
          currencySign: "accounting"
        };
      case "sign-always":
      case "+!":
        return {
          signDisplay: "always"
        };
      case "sign-accounting-always":
      case "()!":
        return {
          signDisplay: "always",
          currencySign: "accounting"
        };
      case "sign-except-zero":
      case "+?":
        return {
          signDisplay: "exceptZero"
        };
      case "sign-accounting-except-zero":
      case "()?":
        return {
          signDisplay: "exceptZero",
          currencySign: "accounting"
        };
      case "sign-never":
      case "+_":
        return {
          signDisplay: "never"
        };
    }
  }
  function Vt(t) {
    var e;
    if ("E" === t[0] && "E" === t[1] ? (e = {
      notation: "engineering"
    }, t = t.slice(2)) : "E" === t[0] && (e = {
      notation: "scientific"
    }, t = t.slice(1)), e) {
      var r = t.slice(0, 2);
      if ("+!" === r ? (e.signDisplay = "always", t = t.slice(2)) : "+?" === r && (e.signDisplay = "exceptZero", t = t.slice(2)), !Dt.test(t)) throw new Error("Malformed concise eng/scientific notation");
      e.minimumIntegerDigits = t.length;
    }
    return e;
  }
  function jt(t) {
    var e = Ft(t);
    return e || {};
  }
  function Xt(t) {
    for (var e = {}, r = 0, n = t; r < n.length; r++) {
      var o = n[r];
      switch (o.stem) {
        case "percent":
        case "%":
          e.style = "percent";
          continue;
        case "%x100":
          e.style = "percent", e.scale = 100;
          continue;
        case "currency":
          e.style = "currency", e.currency = o.options[0];
          continue;
        case "group-off":
        case ",_":
          e.useGrouping = !1;
          continue;
        case "precision-integer":
        case ".":
          e.maximumFractionDigits = 0;
          continue;
        case "measure-unit":
        case "unit":
          e.style = "unit", e.unit = o.options[0].replace(/^(.*?)-/, "");
          continue;
        case "compact-short":
        case "K":
          e.notation = "compact", e.compactDisplay = "short";
          continue;
        case "compact-long":
        case "KK":
          e.notation = "compact", e.compactDisplay = "long";
          continue;
        case "scientific":
          e = i(i(i({}, e), {
            notation: "scientific"
          }), o.options.reduce(function (t, e) {
            return i(i({}, t), jt(e));
          }, {}));
          continue;
        case "engineering":
          e = i(i(i({}, e), {
            notation: "engineering"
          }), o.options.reduce(function (t, e) {
            return i(i({}, t), jt(e));
          }, {}));
          continue;
        case "notation-simple":
          e.notation = "standard";
          continue;
        case "unit-width-narrow":
          e.currencyDisplay = "narrowSymbol", e.unitDisplay = "narrow";
          continue;
        case "unit-width-short":
          e.currencyDisplay = "code", e.unitDisplay = "short";
          continue;
        case "unit-width-full-name":
          e.currencyDisplay = "name", e.unitDisplay = "long";
          continue;
        case "unit-width-iso-code":
          e.currencyDisplay = "symbol";
          continue;
        case "scale":
          e.scale = parseFloat(o.options[0]);
          continue;
        case "rounding-mode-floor":
          e.roundingMode = "floor";
          continue;
        case "rounding-mode-ceiling":
          e.roundingMode = "ceil";
          continue;
        case "rounding-mode-down":
          e.roundingMode = "trunc";
          continue;
        case "rounding-mode-up":
          e.roundingMode = "expand";
          continue;
        case "rounding-mode-half-even":
          e.roundingMode = "halfEven";
          continue;
        case "rounding-mode-half-down":
          e.roundingMode = "halfTrunc";
          continue;
        case "rounding-mode-half-up":
          e.roundingMode = "halfExpand";
          continue;
        case "integer-width":
          if (o.options.length > 1) throw new RangeError("integer-width stems only accept a single optional option");
          o.options[0].replace(Gt, function (t, r, i, n, o, s) {
            if (r) e.minimumIntegerDigits = i.length;else {
              if (n && o) throw new Error("We currently do not support maximum integer digits");
              if (s) throw new Error("We currently do not support exact integer digits");
            }
            return "";
          });
          continue;
      }
      if (Dt.test(o.stem)) e.minimumIntegerDigits = o.stem.length;else if (Mt.test(o.stem)) {
        if (o.options.length > 1) throw new RangeError("Fraction-precision stems only accept a single optional option");
        o.stem.replace(Mt, function (t, r, i, n, o, s) {
          return "*" === i ? e.minimumFractionDigits = r.length : n && "#" === n[0] ? e.maximumFractionDigits = n.length : o && s ? (e.minimumFractionDigits = o.length, e.maximumFractionDigits = o.length + s.length) : (e.minimumFractionDigits = r.length, e.maximumFractionDigits = r.length), "";
        });
        var s = o.options[0];
        "w" === s ? e = i(i({}, e), {
          trailingZeroDisplay: "stripIfInteger"
        }) : s && (e = i(i({}, e), kt(s)));
      } else if (xt.test(o.stem)) e = i(i({}, e), kt(o.stem));else {
        var a = Ft(o.stem);
        a && (e = i(i({}, e), a));
        var h = Vt(o.stem);
        h && (e = i(i({}, e), h));
      }
    }
    return e;
  }
  var Kt,
    zt = {
      "001": ["H", "h"],
      AC: ["H", "h", "hb", "hB"],
      AD: ["H", "hB"],
      AE: ["h", "hB", "hb", "H"],
      AF: ["H", "hb", "hB", "h"],
      AG: ["h", "hb", "H", "hB"],
      AI: ["H", "h", "hb", "hB"],
      AL: ["h", "H", "hB"],
      AM: ["H", "hB"],
      AO: ["H", "hB"],
      AR: ["H", "h", "hB", "hb"],
      AS: ["h", "H"],
      AT: ["H", "hB"],
      AU: ["h", "hb", "H", "hB"],
      AW: ["H", "hB"],
      AX: ["H"],
      AZ: ["H", "hB", "h"],
      BA: ["H", "hB", "h"],
      BB: ["h", "hb", "H", "hB"],
      BD: ["h", "hB", "H"],
      BE: ["H", "hB"],
      BF: ["H", "hB"],
      BG: ["H", "hB", "h"],
      BH: ["h", "hB", "hb", "H"],
      BI: ["H", "h"],
      BJ: ["H", "hB"],
      BL: ["H", "hB"],
      BM: ["h", "hb", "H", "hB"],
      BN: ["hb", "hB", "h", "H"],
      BO: ["H", "hB", "h", "hb"],
      BQ: ["H"],
      BR: ["H", "hB"],
      BS: ["h", "hb", "H", "hB"],
      BT: ["h", "H"],
      BW: ["H", "h", "hb", "hB"],
      BY: ["H", "h"],
      BZ: ["H", "h", "hb", "hB"],
      CA: ["h", "hb", "H", "hB"],
      CC: ["H", "h", "hb", "hB"],
      CD: ["hB", "H"],
      CF: ["H", "h", "hB"],
      CG: ["H", "hB"],
      CH: ["H", "hB", "h"],
      CI: ["H", "hB"],
      CK: ["H", "h", "hb", "hB"],
      CL: ["H", "h", "hB", "hb"],
      CM: ["H", "h", "hB"],
      CN: ["H", "hB", "hb", "h"],
      CO: ["h", "H", "hB", "hb"],
      CP: ["H"],
      CR: ["H", "h", "hB", "hb"],
      CU: ["H", "h", "hB", "hb"],
      CV: ["H", "hB"],
      CW: ["H", "hB"],
      CX: ["H", "h", "hb", "hB"],
      CY: ["h", "H", "hb", "hB"],
      CZ: ["H"],
      DE: ["H", "hB"],
      DG: ["H", "h", "hb", "hB"],
      DJ: ["h", "H"],
      DK: ["H"],
      DM: ["h", "hb", "H", "hB"],
      DO: ["h", "H", "hB", "hb"],
      DZ: ["h", "hB", "hb", "H"],
      EA: ["H", "h", "hB", "hb"],
      EC: ["H", "hB", "h", "hb"],
      EE: ["H", "hB"],
      EG: ["h", "hB", "hb", "H"],
      EH: ["h", "hB", "hb", "H"],
      ER: ["h", "H"],
      ES: ["H", "hB", "h", "hb"],
      ET: ["hB", "hb", "h", "H"],
      FI: ["H"],
      FJ: ["h", "hb", "H", "hB"],
      FK: ["H", "h", "hb", "hB"],
      FM: ["h", "hb", "H", "hB"],
      FO: ["H", "h"],
      FR: ["H", "hB"],
      GA: ["H", "hB"],
      GB: ["H", "h", "hb", "hB"],
      GD: ["h", "hb", "H", "hB"],
      GE: ["H", "hB", "h"],
      GF: ["H", "hB"],
      GG: ["H", "h", "hb", "hB"],
      GH: ["h", "H"],
      GI: ["H", "h", "hb", "hB"],
      GL: ["H", "h"],
      GM: ["h", "hb", "H", "hB"],
      GN: ["H", "hB"],
      GP: ["H", "hB"],
      GQ: ["H", "hB", "h", "hb"],
      GR: ["h", "H", "hb", "hB"],
      GT: ["H", "h", "hB", "hb"],
      GU: ["h", "hb", "H", "hB"],
      GW: ["H", "hB"],
      GY: ["h", "hb", "H", "hB"],
      HK: ["h", "hB", "hb", "H"],
      HN: ["H", "h", "hB", "hb"],
      HR: ["H", "hB"],
      HU: ["H", "h"],
      IC: ["H", "h", "hB", "hb"],
      ID: ["H"],
      IE: ["H", "h", "hb", "hB"],
      IL: ["H", "hB"],
      IM: ["H", "h", "hb", "hB"],
      IN: ["h", "H"],
      IO: ["H", "h", "hb", "hB"],
      IQ: ["h", "hB", "hb", "H"],
      IR: ["hB", "H"],
      IS: ["H"],
      IT: ["H", "hB"],
      JE: ["H", "h", "hb", "hB"],
      JM: ["h", "hb", "H", "hB"],
      JO: ["h", "hB", "hb", "H"],
      JP: ["H", "K", "h"],
      KE: ["hB", "hb", "H", "h"],
      KG: ["H", "h", "hB", "hb"],
      KH: ["hB", "h", "H", "hb"],
      KI: ["h", "hb", "H", "hB"],
      KM: ["H", "h", "hB", "hb"],
      KN: ["h", "hb", "H", "hB"],
      KP: ["h", "H", "hB", "hb"],
      KR: ["h", "H", "hB", "hb"],
      KW: ["h", "hB", "hb", "H"],
      KY: ["h", "hb", "H", "hB"],
      KZ: ["H", "hB"],
      LA: ["H", "hb", "hB", "h"],
      LB: ["h", "hB", "hb", "H"],
      LC: ["h", "hb", "H", "hB"],
      LI: ["H", "hB", "h"],
      LK: ["H", "h", "hB", "hb"],
      LR: ["h", "hb", "H", "hB"],
      LS: ["h", "H"],
      LT: ["H", "h", "hb", "hB"],
      LU: ["H", "h", "hB"],
      LV: ["H", "hB", "hb", "h"],
      LY: ["h", "hB", "hb", "H"],
      MA: ["H", "h", "hB", "hb"],
      MC: ["H", "hB"],
      MD: ["H", "hB"],
      ME: ["H", "hB", "h"],
      MF: ["H", "hB"],
      MG: ["H", "h"],
      MH: ["h", "hb", "H", "hB"],
      MK: ["H", "h", "hb", "hB"],
      ML: ["H"],
      MM: ["hB", "hb", "H", "h"],
      MN: ["H", "h", "hb", "hB"],
      MO: ["h", "hB", "hb", "H"],
      MP: ["h", "hb", "H", "hB"],
      MQ: ["H", "hB"],
      MR: ["h", "hB", "hb", "H"],
      MS: ["H", "h", "hb", "hB"],
      MT: ["H", "h"],
      MU: ["H", "h"],
      MV: ["H", "h"],
      MW: ["h", "hb", "H", "hB"],
      MX: ["H", "h", "hB", "hb"],
      MY: ["hb", "hB", "h", "H"],
      MZ: ["H", "hB"],
      NA: ["h", "H", "hB", "hb"],
      NC: ["H", "hB"],
      NE: ["H"],
      NF: ["H", "h", "hb", "hB"],
      NG: ["H", "h", "hb", "hB"],
      NI: ["H", "h", "hB", "hb"],
      NL: ["H", "hB"],
      NO: ["H", "h"],
      NP: ["H", "h", "hB"],
      NR: ["H", "h", "hb", "hB"],
      NU: ["H", "h", "hb", "hB"],
      NZ: ["h", "hb", "H", "hB"],
      OM: ["h", "hB", "hb", "H"],
      PA: ["h", "H", "hB", "hb"],
      PE: ["H", "hB", "h", "hb"],
      PF: ["H", "h", "hB"],
      PG: ["h", "H"],
      PH: ["h", "hB", "hb", "H"],
      PK: ["h", "hB", "H"],
      PL: ["H", "h"],
      PM: ["H", "hB"],
      PN: ["H", "h", "hb", "hB"],
      PR: ["h", "H", "hB", "hb"],
      PS: ["h", "hB", "hb", "H"],
      PT: ["H", "hB"],
      PW: ["h", "H"],
      PY: ["H", "h", "hB", "hb"],
      QA: ["h", "hB", "hb", "H"],
      RE: ["H", "hB"],
      RO: ["H", "hB"],
      RS: ["H", "hB", "h"],
      RU: ["H"],
      RW: ["H", "h"],
      SA: ["h", "hB", "hb", "H"],
      SB: ["h", "hb", "H", "hB"],
      SC: ["H", "h", "hB"],
      SD: ["h", "hB", "hb", "H"],
      SE: ["H"],
      SG: ["h", "hb", "H", "hB"],
      SH: ["H", "h", "hb", "hB"],
      SI: ["H", "hB"],
      SJ: ["H"],
      SK: ["H"],
      SL: ["h", "hb", "H", "hB"],
      SM: ["H", "h", "hB"],
      SN: ["H", "h", "hB"],
      SO: ["h", "H"],
      SR: ["H", "hB"],
      SS: ["h", "hb", "H", "hB"],
      ST: ["H", "hB"],
      SV: ["H", "h", "hB", "hb"],
      SX: ["H", "h", "hb", "hB"],
      SY: ["h", "hB", "hb", "H"],
      SZ: ["h", "hb", "H", "hB"],
      TA: ["H", "h", "hb", "hB"],
      TC: ["h", "hb", "H", "hB"],
      TD: ["h", "H", "hB"],
      TF: ["H", "h", "hB"],
      TG: ["H", "hB"],
      TH: ["H", "h"],
      TJ: ["H", "h"],
      TL: ["H", "hB", "hb", "h"],
      TM: ["H", "h"],
      TN: ["h", "hB", "hb", "H"],
      TO: ["h", "H"],
      TR: ["H", "hB"],
      TT: ["h", "hb", "H", "hB"],
      TW: ["hB", "hb", "h", "H"],
      TZ: ["hB", "hb", "H", "h"],
      UA: ["H", "hB", "h"],
      UG: ["hB", "hb", "H", "h"],
      UM: ["h", "hb", "H", "hB"],
      US: ["h", "hb", "H", "hB"],
      UY: ["H", "h", "hB", "hb"],
      UZ: ["H", "hB", "h"],
      VA: ["H", "h", "hB"],
      VC: ["h", "hb", "H", "hB"],
      VE: ["h", "H", "hB", "hb"],
      VG: ["h", "hb", "H", "hB"],
      VI: ["h", "hb", "H", "hB"],
      VN: ["H", "h"],
      VU: ["h", "H"],
      WF: ["H", "hB"],
      WS: ["h", "H"],
      XK: ["H", "hB", "h"],
      YE: ["h", "hB", "hb", "H"],
      YT: ["H", "hB"],
      ZA: ["H", "h", "hb", "hB"],
      ZM: ["h", "hb", "H", "hB"],
      ZW: ["H", "h"],
      "af-ZA": ["H", "h", "hB", "hb"],
      "ar-001": ["h", "hB", "hb", "H"],
      "ca-ES": ["H", "h", "hB"],
      "en-001": ["h", "hb", "H", "hB"],
      "es-BO": ["H", "h", "hB", "hb"],
      "es-BR": ["H", "h", "hB", "hb"],
      "es-EC": ["H", "h", "hB", "hb"],
      "es-ES": ["H", "h", "hB", "hb"],
      "es-GQ": ["H", "h", "hB", "hb"],
      "es-PE": ["H", "h", "hB", "hb"],
      "fr-CA": ["H", "h", "hB"],
      "gl-ES": ["H", "h", "hB"],
      "gu-IN": ["hB", "hb", "h", "H"],
      "hi-IN": ["hB", "h", "H"],
      "it-CH": ["H", "h", "hB"],
      "it-IT": ["H", "h", "hB"],
      "kn-IN": ["hB", "h", "H"],
      "ml-IN": ["hB", "h", "H"],
      "mr-IN": ["hB", "hb", "h", "H"],
      "pa-IN": ["hB", "hb", "h", "H"],
      "ta-IN": ["hB", "h", "hb", "H"],
      "te-IN": ["hB", "h", "H"],
      "zu-ZA": ["H", "hB", "hb", "h"]
    };
  function Yt(t) {
    var e = t.hourCycle;
    if (void 0 === e && t.hourCycles && t.hourCycles.length && (e = t.hourCycles[0]), e) switch (e) {
      case "h24":
        return "k";
      case "h23":
        return "H";
      case "h12":
        return "h";
      case "h11":
        return "K";
      default:
        throw new Error("Invalid hourCycle");
    }
    var r,
      i = t.language;
    return "root" !== i && (r = t.maximize().region), (zt[r || ""] || zt[i || ""] || zt["".concat(i, "-001")] || zt["001"])[0];
  }
  var Wt = new RegExp("^".concat(Rt.source, "*")),
    Zt = new RegExp("".concat(Rt.source, "*$"));
  function qt(t, e) {
    return {
      start: t,
      end: e
    };
  }
  var Jt = !!String.prototype.startsWith && "_a".startsWith("a", 1),
    Qt = !!String.fromCodePoint,
    te = !!Object.fromEntries,
    ee = !!String.prototype.codePointAt,
    re = !!String.prototype.trimStart,
    ie = !!String.prototype.trimEnd,
    ne = !!Number.isSafeInteger ? Number.isSafeInteger : function (t) {
      return "number" == typeof t && isFinite(t) && Math.floor(t) === t && Math.abs(t) <= 9007199254740991;
    },
    oe = !0;
  try {
    oe = "a" === (null === (Kt = de("([^\\p{White_Space}\\p{Pattern_Syntax}]*)", "yu").exec("a")) || void 0 === Kt ? void 0 : Kt[0]);
  } catch (M) {
    oe = !1;
  }
  var se,
    ae = Jt ? function (t, e, r) {
      return t.startsWith(e, r);
    } : function (t, e, r) {
      return t.slice(r, r + e.length) === e;
    },
    he = Qt ? String.fromCodePoint : function () {
      for (var t = [], e = 0; e < arguments.length; e++) t[e] = arguments[e];
      for (var r, i = "", n = t.length, o = 0; n > o;) {
        if ((r = t[o++]) > 1114111) throw RangeError(r + " is not a valid code point");
        i += r < 65536 ? String.fromCharCode(r) : String.fromCharCode(55296 + ((r -= 65536) >> 10), r % 1024 + 56320);
      }
      return i;
    },
    le = te ? Object.fromEntries : function (t) {
      for (var e = {}, r = 0, i = t; r < i.length; r++) {
        var n = i[r],
          o = n[0],
          s = n[1];
        e[o] = s;
      }
      return e;
    },
    ce = ee ? function (t, e) {
      return t.codePointAt(e);
    } : function (t, e) {
      var r = t.length;
      if (!(e < 0 || e >= r)) {
        var i,
          n = t.charCodeAt(e);
        return n < 55296 || n > 56319 || e + 1 === r || (i = t.charCodeAt(e + 1)) < 56320 || i > 57343 ? n : i - 56320 + (n - 55296 << 10) + 65536;
      }
    },
    ue = re ? function (t) {
      return t.trimStart();
    } : function (t) {
      return t.replace(Wt, "");
    },
    pe = ie ? function (t) {
      return t.trimEnd();
    } : function (t) {
      return t.replace(Zt, "");
    };
  function de(t, e) {
    return new RegExp(t, e);
  }
  if (oe) {
    var fe = de("([^\\p{White_Space}\\p{Pattern_Syntax}]*)", "yu");
    se = function (t, e) {
      var r;
      return fe.lastIndex = e, null !== (r = fe.exec(t)[1]) && void 0 !== r ? r : "";
    };
  } else se = function (t, e) {
    for (var r = [];;) {
      var i = ce(t, e);
      if (void 0 === i || Ee(i) || be(i)) break;
      r.push(i), e += i >= 65536 ? 2 : 1;
    }
    return he.apply(void 0, r);
  };
  var me = function () {
    function t(t, e) {
      void 0 === e && (e = {}), this.message = t, this.position = {
        offset: 0,
        line: 1,
        column: 1
      }, this.ignoreTag = !!e.ignoreTag, this.locale = e.locale, this.requiresOtherClause = !!e.requiresOtherClause, this.shouldParseSkeletons = !!e.shouldParseSkeletons;
    }
    return t.prototype.parse = function () {
      if (0 !== this.offset()) throw Error("parser can only be used once");
      return this.parseMessage(0, "", !1);
    }, t.prototype.parseMessage = function (t, e, r) {
      for (var i = []; !this.isEOF();) {
        var n = this.char();
        if (123 === n) {
          if ((o = this.parseArgument(t, r)).err) return o;
          i.push(o.val);
        } else {
          if (125 === n && t > 0) break;
          if (35 !== n || "plural" !== e && "selectordinal" !== e) {
            if (60 === n && !this.ignoreTag && 47 === this.peek()) {
              if (r) break;
              return this.error(mt.UNMATCHED_CLOSING_TAG, qt(this.clonePosition(), this.clonePosition()));
            }
            if (60 === n && !this.ignoreTag && ge(this.peek() || 0)) {
              if ((o = this.parseTag(t, e)).err) return o;
              i.push(o.val);
            } else {
              var o;
              if ((o = this.parseLiteral(t, e)).err) return o;
              i.push(o.val);
            }
          } else {
            var s = this.clonePosition();
            this.bump(), i.push({
              type: gt.pound,
              location: qt(s, this.clonePosition())
            });
          }
        }
      }
      return {
        val: i,
        err: null
      };
    }, t.prototype.parseTag = function (t, e) {
      var r = this.clonePosition();
      this.bump();
      var i = this.parseTagName();
      if (this.bumpSpace(), this.bumpIf("/>")) return {
        val: {
          type: gt.literal,
          value: "<".concat(i, "/>"),
          location: qt(r, this.clonePosition())
        },
        err: null
      };
      if (this.bumpIf(">")) {
        var n = this.parseMessage(t + 1, e, !0);
        if (n.err) return n;
        var o = n.val,
          s = this.clonePosition();
        if (this.bumpIf("</")) {
          if (this.isEOF() || !ge(this.char())) return this.error(mt.INVALID_TAG, qt(s, this.clonePosition()));
          var a = this.clonePosition();
          return i !== this.parseTagName() ? this.error(mt.UNMATCHED_CLOSING_TAG, qt(a, this.clonePosition())) : (this.bumpSpace(), this.bumpIf(">") ? {
            val: {
              type: gt.tag,
              value: i,
              children: o,
              location: qt(r, this.clonePosition())
            },
            err: null
          } : this.error(mt.INVALID_TAG, qt(s, this.clonePosition())));
        }
        return this.error(mt.UNCLOSED_TAG, qt(r, this.clonePosition()));
      }
      return this.error(mt.INVALID_TAG, qt(r, this.clonePosition()));
    }, t.prototype.parseTagName = function () {
      var t = this.offset();
      for (this.bump(); !this.isEOF() && ve(this.char());) this.bump();
      return this.message.slice(t, this.offset());
    }, t.prototype.parseLiteral = function (t, e) {
      for (var r = this.clonePosition(), i = "";;) {
        var n = this.tryParseQuote(e);
        if (n) i += n;else {
          var o = this.tryParseUnquoted(t, e);
          if (o) i += o;else {
            var s = this.tryParseLeftAngleBracket();
            if (!s) break;
            i += s;
          }
        }
      }
      var a = qt(r, this.clonePosition());
      return {
        val: {
          type: gt.literal,
          value: i,
          location: a
        },
        err: null
      };
    }, t.prototype.tryParseLeftAngleBracket = function () {
      return this.isEOF() || 60 !== this.char() || !this.ignoreTag && (ge(t = this.peek() || 0) || 47 === t) ? null : (this.bump(), "<");
      var t;
    }, t.prototype.tryParseQuote = function (t) {
      if (this.isEOF() || 39 !== this.char()) return null;
      switch (this.peek()) {
        case 39:
          return this.bump(), this.bump(), "'";
        case 123:
        case 60:
        case 62:
        case 125:
          break;
        case 35:
          if ("plural" === t || "selectordinal" === t) break;
          return null;
        default:
          return null;
      }
      this.bump();
      var e = [this.char()];
      for (this.bump(); !this.isEOF();) {
        var r = this.char();
        if (39 === r) {
          if (39 !== this.peek()) {
            this.bump();
            break;
          }
          e.push(39), this.bump();
        } else e.push(r);
        this.bump();
      }
      return he.apply(void 0, e);
    }, t.prototype.tryParseUnquoted = function (t, e) {
      if (this.isEOF()) return null;
      var r = this.char();
      return 60 === r || 123 === r || 35 === r && ("plural" === e || "selectordinal" === e) || 125 === r && t > 0 ? null : (this.bump(), he(r));
    }, t.prototype.parseArgument = function (t, e) {
      var r = this.clonePosition();
      if (this.bump(), this.bumpSpace(), this.isEOF()) return this.error(mt.EXPECT_ARGUMENT_CLOSING_BRACE, qt(r, this.clonePosition()));
      if (125 === this.char()) return this.bump(), this.error(mt.EMPTY_ARGUMENT, qt(r, this.clonePosition()));
      var i = this.parseIdentifierIfPossible().value;
      if (!i) return this.error(mt.MALFORMED_ARGUMENT, qt(r, this.clonePosition()));
      if (this.bumpSpace(), this.isEOF()) return this.error(mt.EXPECT_ARGUMENT_CLOSING_BRACE, qt(r, this.clonePosition()));
      switch (this.char()) {
        case 125:
          return this.bump(), {
            val: {
              type: gt.argument,
              value: i,
              location: qt(r, this.clonePosition())
            },
            err: null
          };
        case 44:
          return this.bump(), this.bumpSpace(), this.isEOF() ? this.error(mt.EXPECT_ARGUMENT_CLOSING_BRACE, qt(r, this.clonePosition())) : this.parseArgumentOptions(t, e, i, r);
        default:
          return this.error(mt.MALFORMED_ARGUMENT, qt(r, this.clonePosition()));
      }
    }, t.prototype.parseIdentifierIfPossible = function () {
      var t = this.clonePosition(),
        e = this.offset(),
        r = se(this.message, e),
        i = e + r.length;
      return this.bumpTo(i), {
        value: r,
        location: qt(t, this.clonePosition())
      };
    }, t.prototype.parseArgumentOptions = function (t, e, r, n) {
      var o,
        s = this.clonePosition(),
        a = this.parseIdentifierIfPossible().value,
        h = this.clonePosition();
      switch (a) {
        case "":
          return this.error(mt.EXPECT_ARGUMENT_TYPE, qt(s, h));
        case "number":
        case "date":
        case "time":
          this.bumpSpace();
          var l = null;
          if (this.bumpIf(",")) {
            this.bumpSpace();
            var c = this.clonePosition();
            if ((E = this.parseSimpleArgStyleIfPossible()).err) return E;
            if (0 === (f = pe(E.val)).length) return this.error(mt.EXPECT_ARGUMENT_STYLE, qt(this.clonePosition(), this.clonePosition()));
            l = {
              style: f,
              styleLocation: qt(c, this.clonePosition())
            };
          }
          if ((b = this.tryParseArgumentClose(n)).err) return b;
          var u = qt(n, this.clonePosition());
          if (l && ae(null == l ? void 0 : l.style, "::", 0)) {
            var p = ue(l.style.slice(2));
            if ("number" === a) return (E = this.parseNumberSkeletonFromString(p, l.styleLocation)).err ? E : {
              val: {
                type: gt.number,
                value: r,
                location: u,
                style: E.val
              },
              err: null
            };
            if (0 === p.length) return this.error(mt.EXPECT_DATE_TIME_SKELETON, u);
            var d = p;
            this.locale && (d = function (t, e) {
              for (var r = "", i = 0; i < t.length; i++) {
                var n = t.charAt(i);
                if ("j" === n) {
                  for (var o = 0; i + 1 < t.length && t.charAt(i + 1) === n;) o++, i++;
                  var s = 1 + (1 & o),
                    a = o < 2 ? 1 : 3 + (o >> 1),
                    h = Yt(e);
                  for ("H" != h && "k" != h || (a = 0); a-- > 0;) r += "a";
                  for (; s-- > 0;) r = h + r;
                } else r += "J" === n ? "H" : n;
              }
              return r;
            }(p, this.locale));
            var f = {
              type: vt.dateTime,
              pattern: d,
              location: l.styleLocation,
              parsedOptions: this.shouldParseSkeletons ? Ot(d) : {}
            };
            return {
              val: {
                type: "date" === a ? gt.date : gt.time,
                value: r,
                location: u,
                style: f
              },
              err: null
            };
          }
          return {
            val: {
              type: "number" === a ? gt.number : "date" === a ? gt.date : gt.time,
              value: r,
              location: u,
              style: null !== (o = null == l ? void 0 : l.style) && void 0 !== o ? o : null
            },
            err: null
          };
        case "plural":
        case "selectordinal":
        case "select":
          var m = this.clonePosition();
          if (this.bumpSpace(), !this.bumpIf(",")) return this.error(mt.EXPECT_SELECT_ARGUMENT_OPTIONS, qt(m, i({}, m)));
          this.bumpSpace();
          var g = this.parseIdentifierIfPossible(),
            v = 0;
          if ("select" !== a && "offset" === g.value) {
            if (!this.bumpIf(":")) return this.error(mt.EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE, qt(this.clonePosition(), this.clonePosition()));
            var E;
            if (this.bumpSpace(), (E = this.tryParseDecimalInteger(mt.EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE, mt.INVALID_PLURAL_ARGUMENT_OFFSET_VALUE)).err) return E;
            this.bumpSpace(), g = this.parseIdentifierIfPossible(), v = E.val;
          }
          var b,
            y = this.tryParsePluralOrSelectOptions(t, a, e, g);
          if (y.err) return y;
          if ((b = this.tryParseArgumentClose(n)).err) return b;
          var _ = qt(n, this.clonePosition());
          return "select" === a ? {
            val: {
              type: gt.select,
              value: r,
              options: le(y.val),
              location: _
            },
            err: null
          } : {
            val: {
              type: gt.plural,
              value: r,
              options: le(y.val),
              offset: v,
              pluralType: "plural" === a ? "cardinal" : "ordinal",
              location: _
            },
            err: null
          };
        default:
          return this.error(mt.INVALID_ARGUMENT_TYPE, qt(s, h));
      }
    }, t.prototype.tryParseArgumentClose = function (t) {
      return this.isEOF() || 125 !== this.char() ? this.error(mt.EXPECT_ARGUMENT_CLOSING_BRACE, qt(t, this.clonePosition())) : (this.bump(), {
        val: !0,
        err: null
      });
    }, t.prototype.parseSimpleArgStyleIfPossible = function () {
      for (var t = 0, e = this.clonePosition(); !this.isEOF();) {
        switch (this.char()) {
          case 39:
            this.bump();
            var r = this.clonePosition();
            if (!this.bumpUntil("'")) return this.error(mt.UNCLOSED_QUOTE_IN_ARGUMENT_STYLE, qt(r, this.clonePosition()));
            this.bump();
            break;
          case 123:
            t += 1, this.bump();
            break;
          case 125:
            if (!(t > 0)) return {
              val: this.message.slice(e.offset, this.offset()),
              err: null
            };
            t -= 1;
            break;
          default:
            this.bump();
        }
      }
      return {
        val: this.message.slice(e.offset, this.offset()),
        err: null
      };
    }, t.prototype.parseNumberSkeletonFromString = function (t, e) {
      var r = [];
      try {
        r = function (t) {
          if (0 === t.length) throw new Error("Number skeleton cannot be empty");
          for (var e = t.split(Ut).filter(function (t) {
              return t.length > 0;
            }), r = [], i = 0, n = e; i < n.length; i++) {
            var o = n[i].split("/");
            if (0 === o.length) throw new Error("Invalid number skeleton");
            for (var s = o[0], a = o.slice(1), h = 0, l = a; h < l.length; h++) if (0 === l[h].length) throw new Error("Invalid number skeleton");
            r.push({
              stem: s,
              options: a
            });
          }
          return r;
        }(t);
      } catch (t) {
        return this.error(mt.INVALID_NUMBER_SKELETON, e);
      }
      return {
        val: {
          type: vt.number,
          tokens: r,
          location: e,
          parsedOptions: this.shouldParseSkeletons ? Xt(r) : {}
        },
        err: null
      };
    }, t.prototype.tryParsePluralOrSelectOptions = function (t, e, r, i) {
      for (var n, o = !1, s = [], a = new Set(), h = i.value, l = i.location;;) {
        if (0 === h.length) {
          var c = this.clonePosition();
          if ("select" === e || !this.bumpIf("=")) break;
          var u = this.tryParseDecimalInteger(mt.EXPECT_PLURAL_ARGUMENT_SELECTOR, mt.INVALID_PLURAL_ARGUMENT_SELECTOR);
          if (u.err) return u;
          l = qt(c, this.clonePosition()), h = this.message.slice(c.offset, this.offset());
        }
        if (a.has(h)) return this.error("select" === e ? mt.DUPLICATE_SELECT_ARGUMENT_SELECTOR : mt.DUPLICATE_PLURAL_ARGUMENT_SELECTOR, l);
        "other" === h && (o = !0), this.bumpSpace();
        var p = this.clonePosition();
        if (!this.bumpIf("{")) return this.error("select" === e ? mt.EXPECT_SELECT_ARGUMENT_SELECTOR_FRAGMENT : mt.EXPECT_PLURAL_ARGUMENT_SELECTOR_FRAGMENT, qt(this.clonePosition(), this.clonePosition()));
        var d = this.parseMessage(t + 1, e, r);
        if (d.err) return d;
        var f = this.tryParseArgumentClose(p);
        if (f.err) return f;
        s.push([h, {
          value: d.val,
          location: qt(p, this.clonePosition())
        }]), a.add(h), this.bumpSpace(), h = (n = this.parseIdentifierIfPossible()).value, l = n.location;
      }
      return 0 === s.length ? this.error("select" === e ? mt.EXPECT_SELECT_ARGUMENT_SELECTOR : mt.EXPECT_PLURAL_ARGUMENT_SELECTOR, qt(this.clonePosition(), this.clonePosition())) : this.requiresOtherClause && !o ? this.error(mt.MISSING_OTHER_CLAUSE, qt(this.clonePosition(), this.clonePosition())) : {
        val: s,
        err: null
      };
    }, t.prototype.tryParseDecimalInteger = function (t, e) {
      var r = 1,
        i = this.clonePosition();
      this.bumpIf("+") || this.bumpIf("-") && (r = -1);
      for (var n = !1, o = 0; !this.isEOF();) {
        var s = this.char();
        if (!(s >= 48 && s <= 57)) break;
        n = !0, o = 10 * o + (s - 48), this.bump();
      }
      var a = qt(i, this.clonePosition());
      return n ? ne(o *= r) ? {
        val: o,
        err: null
      } : this.error(e, a) : this.error(t, a);
    }, t.prototype.offset = function () {
      return this.position.offset;
    }, t.prototype.isEOF = function () {
      return this.offset() === this.message.length;
    }, t.prototype.clonePosition = function () {
      return {
        offset: this.position.offset,
        line: this.position.line,
        column: this.position.column
      };
    }, t.prototype.char = function () {
      var t = this.position.offset;
      if (t >= this.message.length) throw Error("out of bound");
      var e = ce(this.message, t);
      if (void 0 === e) throw Error("Offset ".concat(t, " is at invalid UTF-16 code unit boundary"));
      return e;
    }, t.prototype.error = function (t, e) {
      return {
        val: null,
        err: {
          kind: t,
          message: this.message,
          location: e
        }
      };
    }, t.prototype.bump = function () {
      if (!this.isEOF()) {
        var t = this.char();
        10 === t ? (this.position.line += 1, this.position.column = 1, this.position.offset += 1) : (this.position.column += 1, this.position.offset += t < 65536 ? 1 : 2);
      }
    }, t.prototype.bumpIf = function (t) {
      if (ae(this.message, t, this.offset())) {
        for (var e = 0; e < t.length; e++) this.bump();
        return !0;
      }
      return !1;
    }, t.prototype.bumpUntil = function (t) {
      var e = this.offset(),
        r = this.message.indexOf(t, e);
      return r >= 0 ? (this.bumpTo(r), !0) : (this.bumpTo(this.message.length), !1);
    }, t.prototype.bumpTo = function (t) {
      if (this.offset() > t) throw Error("targetOffset ".concat(t, " must be greater than or equal to the current offset ").concat(this.offset()));
      for (t = Math.min(t, this.message.length);;) {
        var e = this.offset();
        if (e === t) break;
        if (e > t) throw Error("targetOffset ".concat(t, " is at invalid UTF-16 code unit boundary"));
        if (this.bump(), this.isEOF()) break;
      }
    }, t.prototype.bumpSpace = function () {
      for (; !this.isEOF() && Ee(this.char());) this.bump();
    }, t.prototype.peek = function () {
      if (this.isEOF()) return null;
      var t = this.char(),
        e = this.offset(),
        r = this.message.charCodeAt(e + (t >= 65536 ? 2 : 1));
      return null != r ? r : null;
    }, t;
  }();
  function ge(t) {
    return t >= 97 && t <= 122 || t >= 65 && t <= 90;
  }
  function ve(t) {
    return 45 === t || 46 === t || t >= 48 && t <= 57 || 95 === t || t >= 97 && t <= 122 || t >= 65 && t <= 90 || 183 == t || t >= 192 && t <= 214 || t >= 216 && t <= 246 || t >= 248 && t <= 893 || t >= 895 && t <= 8191 || t >= 8204 && t <= 8205 || t >= 8255 && t <= 8256 || t >= 8304 && t <= 8591 || t >= 11264 && t <= 12271 || t >= 12289 && t <= 55295 || t >= 63744 && t <= 64975 || t >= 65008 && t <= 65533 || t >= 65536 && t <= 983039;
  }
  function Ee(t) {
    return t >= 9 && t <= 13 || 32 === t || 133 === t || t >= 8206 && t <= 8207 || 8232 === t || 8233 === t;
  }
  function be(t) {
    return t >= 33 && t <= 35 || 36 === t || t >= 37 && t <= 39 || 40 === t || 41 === t || 42 === t || 43 === t || 44 === t || 45 === t || t >= 46 && t <= 47 || t >= 58 && t <= 59 || t >= 60 && t <= 62 || t >= 63 && t <= 64 || 91 === t || 92 === t || 93 === t || 94 === t || 96 === t || 123 === t || 124 === t || 125 === t || 126 === t || 161 === t || t >= 162 && t <= 165 || 166 === t || 167 === t || 169 === t || 171 === t || 172 === t || 174 === t || 176 === t || 177 === t || 182 === t || 187 === t || 191 === t || 215 === t || 247 === t || t >= 8208 && t <= 8213 || t >= 8214 && t <= 8215 || 8216 === t || 8217 === t || 8218 === t || t >= 8219 && t <= 8220 || 8221 === t || 8222 === t || 8223 === t || t >= 8224 && t <= 8231 || t >= 8240 && t <= 8248 || 8249 === t || 8250 === t || t >= 8251 && t <= 8254 || t >= 8257 && t <= 8259 || 8260 === t || 8261 === t || 8262 === t || t >= 8263 && t <= 8273 || 8274 === t || 8275 === t || t >= 8277 && t <= 8286 || t >= 8592 && t <= 8596 || t >= 8597 && t <= 8601 || t >= 8602 && t <= 8603 || t >= 8604 && t <= 8607 || 8608 === t || t >= 8609 && t <= 8610 || 8611 === t || t >= 8612 && t <= 8613 || 8614 === t || t >= 8615 && t <= 8621 || 8622 === t || t >= 8623 && t <= 8653 || t >= 8654 && t <= 8655 || t >= 8656 && t <= 8657 || 8658 === t || 8659 === t || 8660 === t || t >= 8661 && t <= 8691 || t >= 8692 && t <= 8959 || t >= 8960 && t <= 8967 || 8968 === t || 8969 === t || 8970 === t || 8971 === t || t >= 8972 && t <= 8991 || t >= 8992 && t <= 8993 || t >= 8994 && t <= 9e3 || 9001 === t || 9002 === t || t >= 9003 && t <= 9083 || 9084 === t || t >= 9085 && t <= 9114 || t >= 9115 && t <= 9139 || t >= 9140 && t <= 9179 || t >= 9180 && t <= 9185 || t >= 9186 && t <= 9254 || t >= 9255 && t <= 9279 || t >= 9280 && t <= 9290 || t >= 9291 && t <= 9311 || t >= 9472 && t <= 9654 || 9655 === t || t >= 9656 && t <= 9664 || 9665 === t || t >= 9666 && t <= 9719 || t >= 9720 && t <= 9727 || t >= 9728 && t <= 9838 || 9839 === t || t >= 9840 && t <= 10087 || 10088 === t || 10089 === t || 10090 === t || 10091 === t || 10092 === t || 10093 === t || 10094 === t || 10095 === t || 10096 === t || 10097 === t || 10098 === t || 10099 === t || 10100 === t || 10101 === t || t >= 10132 && t <= 10175 || t >= 10176 && t <= 10180 || 10181 === t || 10182 === t || t >= 10183 && t <= 10213 || 10214 === t || 10215 === t || 10216 === t || 10217 === t || 10218 === t || 10219 === t || 10220 === t || 10221 === t || 10222 === t || 10223 === t || t >= 10224 && t <= 10239 || t >= 10240 && t <= 10495 || t >= 10496 && t <= 10626 || 10627 === t || 10628 === t || 10629 === t || 10630 === t || 10631 === t || 10632 === t || 10633 === t || 10634 === t || 10635 === t || 10636 === t || 10637 === t || 10638 === t || 10639 === t || 10640 === t || 10641 === t || 10642 === t || 10643 === t || 10644 === t || 10645 === t || 10646 === t || 10647 === t || 10648 === t || t >= 10649 && t <= 10711 || 10712 === t || 10713 === t || 10714 === t || 10715 === t || t >= 10716 && t <= 10747 || 10748 === t || 10749 === t || t >= 10750 && t <= 11007 || t >= 11008 && t <= 11055 || t >= 11056 && t <= 11076 || t >= 11077 && t <= 11078 || t >= 11079 && t <= 11084 || t >= 11085 && t <= 11123 || t >= 11124 && t <= 11125 || t >= 11126 && t <= 11157 || 11158 === t || t >= 11159 && t <= 11263 || t >= 11776 && t <= 11777 || 11778 === t || 11779 === t || 11780 === t || 11781 === t || t >= 11782 && t <= 11784 || 11785 === t || 11786 === t || 11787 === t || 11788 === t || 11789 === t || t >= 11790 && t <= 11798 || 11799 === t || t >= 11800 && t <= 11801 || 11802 === t || 11803 === t || 11804 === t || 11805 === t || t >= 11806 && t <= 11807 || 11808 === t || 11809 === t || 11810 === t || 11811 === t || 11812 === t || 11813 === t || 11814 === t || 11815 === t || 11816 === t || 11817 === t || t >= 11818 && t <= 11822 || 11823 === t || t >= 11824 && t <= 11833 || t >= 11834 && t <= 11835 || t >= 11836 && t <= 11839 || 11840 === t || 11841 === t || 11842 === t || t >= 11843 && t <= 11855 || t >= 11856 && t <= 11857 || 11858 === t || t >= 11859 && t <= 11903 || t >= 12289 && t <= 12291 || 12296 === t || 12297 === t || 12298 === t || 12299 === t || 12300 === t || 12301 === t || 12302 === t || 12303 === t || 12304 === t || 12305 === t || t >= 12306 && t <= 12307 || 12308 === t || 12309 === t || 12310 === t || 12311 === t || 12312 === t || 12313 === t || 12314 === t || 12315 === t || 12316 === t || 12317 === t || t >= 12318 && t <= 12319 || 12320 === t || 12336 === t || 64830 === t || 64831 === t || t >= 65093 && t <= 65094;
  }
  function ye(t) {
    t.forEach(function (t) {
      if (delete t.location, Pt(t) || wt(t)) for (var e in t.options) delete t.options[e].location, ye(t.options[e].value);else Tt(t) && Lt(t.style) || (Bt(t) || St(t)) && $t(t.style) ? delete t.style.location : Nt(t) && ye(t.children);
    });
  }
  function _e(t, e) {
    void 0 === e && (e = {}), e = i({
      shouldParseSkeletons: !0,
      requiresOtherClause: !0
    }, e);
    var r = new me(t, e).parse();
    if (r.err) {
      var n = SyntaxError(mt[r.err.kind]);
      throw n.location = r.err.location, n.originalMessage = r.err.message, n;
    }
    return (null == e ? void 0 : e.captureLocation) || ye(r.val), r.val;
  }
  function Ae(t, e) {
    var r = e && e.cache ? e.cache : Ne,
      i = e && e.serializer ? e.serializer : Pe;
    return (e && e.strategy ? e.strategy : Se)(t, {
      cache: r,
      serializer: i
    });
  }
  function He(t, e, r, i) {
    var n,
      o = null == (n = i) || "number" == typeof n || "boolean" == typeof n ? i : r(i),
      s = e.get(o);
    return void 0 === s && (s = t.call(this, i), e.set(o, s)), s;
  }
  function Te(t, e, r) {
    var i = Array.prototype.slice.call(arguments, 3),
      n = r(i),
      o = e.get(n);
    return void 0 === o && (o = t.apply(this, i), e.set(n, o)), o;
  }
  function Be(t, e, r, i, n) {
    return r.bind(e, t, i, n);
  }
  function Se(t, e) {
    return Be(t, this, 1 === t.length ? He : Te, e.cache.create(), e.serializer);
  }
  var Pe = function () {
    return JSON.stringify(arguments);
  };
  function we() {
    this.cache = Object.create(null);
  }
  we.prototype.get = function (t) {
    return this.cache[t];
  }, we.prototype.set = function (t, e) {
    this.cache[t] = e;
  };
  var Ce,
    Ne = {
      create: function () {
        return new we();
      }
    },
    Le = {
      variadic: function (t, e) {
        return Be(t, this, Te, e.cache.create(), e.serializer);
      },
      monadic: function (t, e) {
        return Be(t, this, He, e.cache.create(), e.serializer);
      }
    };
  !function (t) {
    t.MISSING_VALUE = "MISSING_VALUE", t.INVALID_VALUE = "INVALID_VALUE", t.MISSING_INTL_API = "MISSING_INTL_API";
  }(Ce || (Ce = {}));
  var $e,
    Re = function (t) {
      function e(e, r, i) {
        var n = t.call(this, e) || this;
        return n.code = r, n.originalMessage = i, n;
      }
      return r(e, t), e.prototype.toString = function () {
        return "[formatjs Error: ".concat(this.code, "] ").concat(this.message);
      }, e;
    }(Error),
    Ie = function (t) {
      function e(e, r, i, n) {
        return t.call(this, 'Invalid values for "'.concat(e, '": "').concat(r, '". Options are "').concat(Object.keys(i).join('", "'), '"'), Ce.INVALID_VALUE, n) || this;
      }
      return r(e, t), e;
    }(Re),
    Oe = function (t) {
      function e(e, r, i) {
        return t.call(this, 'Value for "'.concat(e, '" must be of type ').concat(r), Ce.INVALID_VALUE, i) || this;
      }
      return r(e, t), e;
    }(Re),
    Ue = function (t) {
      function e(e, r) {
        return t.call(this, 'The intl string context variable "'.concat(e, '" was not provided to the string "').concat(r, '"'), Ce.MISSING_VALUE, r) || this;
      }
      return r(e, t), e;
    }(Re);
  function Me(t) {
    return "function" == typeof t;
  }
  function xe(t, e, r, i, n, o, s) {
    if (1 === t.length && At(t[0])) return [{
      type: $e.literal,
      value: t[0].value
    }];
    for (var a = [], h = 0, l = t; h < l.length; h++) {
      var c = l[h];
      if (At(c)) a.push({
        type: $e.literal,
        value: c.value
      });else if (Ct(c)) "number" == typeof o && a.push({
        type: $e.literal,
        value: r.getNumberFormat(e).format(o)
      });else {
        var u = c.value;
        if (!n || !(u in n)) throw new Ue(u, s);
        var p = n[u];
        if (Ht(c)) p && "string" != typeof p && "number" != typeof p || (p = "string" == typeof p || "number" == typeof p ? String(p) : ""), a.push({
          type: "string" == typeof p ? $e.literal : $e.object,
          value: p
        });else if (Bt(c)) {
          var d = "string" == typeof c.style ? i.date[c.style] : $t(c.style) ? c.style.parsedOptions : void 0;
          a.push({
            type: $e.literal,
            value: r.getDateTimeFormat(e, d).format(p)
          });
        } else if (St(c)) {
          d = "string" == typeof c.style ? i.time[c.style] : $t(c.style) ? c.style.parsedOptions : i.time.medium;
          a.push({
            type: $e.literal,
            value: r.getDateTimeFormat(e, d).format(p)
          });
        } else if (Tt(c)) {
          (d = "string" == typeof c.style ? i.number[c.style] : Lt(c.style) ? c.style.parsedOptions : void 0) && d.scale && (p *= d.scale || 1), a.push({
            type: $e.literal,
            value: r.getNumberFormat(e, d).format(p)
          });
        } else {
          if (Nt(c)) {
            var f = c.children,
              m = c.value,
              g = n[m];
            if (!Me(g)) throw new Oe(m, "function", s);
            var v = g(xe(f, e, r, i, n, o).map(function (t) {
              return t.value;
            }));
            Array.isArray(v) || (v = [v]), a.push.apply(a, v.map(function (t) {
              return {
                type: "string" == typeof t ? $e.literal : $e.object,
                value: t
              };
            }));
          }
          if (Pt(c)) {
            if (!(E = c.options[p] || c.options.other)) throw new Ie(c.value, p, Object.keys(c.options), s);
            a.push.apply(a, xe(E.value, e, r, i, n));
          } else if (wt(c)) {
            var E;
            if (!(E = c.options["=".concat(p)])) {
              if (!Intl.PluralRules) throw new Re('Intl.PluralRules is not available in this environment.\nTry polyfilling it using "@formatjs/intl-pluralrules"\n', Ce.MISSING_INTL_API, s);
              var b = r.getPluralRules(e, {
                type: c.pluralType
              }).select(p - (c.offset || 0));
              E = c.options[b] || c.options.other;
            }
            if (!E) throw new Ie(c.value, p, Object.keys(c.options), s);
            a.push.apply(a, xe(E.value, e, r, i, n, p - (c.offset || 0)));
          } else ;
        }
      }
    }
    return function (t) {
      return t.length < 2 ? t : t.reduce(function (t, e) {
        var r = t[t.length - 1];
        return r && r.type === $e.literal && e.type === $e.literal ? r.value += e.value : t.push(e), t;
      }, []);
    }(a);
  }
  function Ge(t, e) {
    return e ? Object.keys(t).reduce(function (r, n) {
      var o, s;
      return r[n] = (o = t[n], (s = e[n]) ? i(i(i({}, o || {}), s || {}), Object.keys(o).reduce(function (t, e) {
        return t[e] = i(i({}, o[e]), s[e] || {}), t;
      }, {})) : o), r;
    }, i({}, t)) : t;
  }
  function De(t) {
    return {
      create: function () {
        return {
          get: function (e) {
            return t[e];
          },
          set: function (e, r) {
            t[e] = r;
          }
        };
      }
    };
  }
  !function (t) {
    t[t.literal = 0] = "literal", t[t.object = 1] = "object";
  }($e || ($e = {}));
  var ke = function () {
      function t(e, r, n, s) {
        var a,
          h = this;
        if (void 0 === r && (r = t.defaultLocale), this.formatterCache = {
          number: {},
          dateTime: {},
          pluralRules: {}
        }, this.format = function (t) {
          var e = h.formatToParts(t);
          if (1 === e.length) return e[0].value;
          var r = e.reduce(function (t, e) {
            return t.length && e.type === $e.literal && "string" == typeof t[t.length - 1] ? t[t.length - 1] += e.value : t.push(e.value), t;
          }, []);
          return r.length <= 1 ? r[0] || "" : r;
        }, this.formatToParts = function (t) {
          return xe(h.ast, h.locales, h.formatters, h.formats, t, void 0, h.message);
        }, this.resolvedOptions = function () {
          var t;
          return {
            locale: (null === (t = h.resolvedLocale) || void 0 === t ? void 0 : t.toString()) || Intl.NumberFormat.supportedLocalesOf(h.locales)[0]
          };
        }, this.getAst = function () {
          return h.ast;
        }, this.locales = r, this.resolvedLocale = t.resolveLocale(r), "string" == typeof e) {
          if (this.message = e, !t.__parse) throw new TypeError("IntlMessageFormat.__parse must be set to process `message` of type `string`");
          var l = s || {};
          l.formatters;
          var c = function (t, e) {
            var r = {};
            for (var i in t) Object.prototype.hasOwnProperty.call(t, i) && e.indexOf(i) < 0 && (r[i] = t[i]);
            if (null != t && "function" == typeof Object.getOwnPropertySymbols) {
              var n = 0;
              for (i = Object.getOwnPropertySymbols(t); n < i.length; n++) e.indexOf(i[n]) < 0 && Object.prototype.propertyIsEnumerable.call(t, i[n]) && (r[i[n]] = t[i[n]]);
            }
            return r;
          }(l, ["formatters"]);
          this.ast = t.__parse(e, i(i({}, c), {
            locale: this.resolvedLocale
          }));
        } else this.ast = e;
        if (!Array.isArray(this.ast)) throw new TypeError("A message must be provided as a String or AST.");
        this.formats = Ge(t.formats, n), this.formatters = s && s.formatters || (void 0 === (a = this.formatterCache) && (a = {
          number: {},
          dateTime: {},
          pluralRules: {}
        }), {
          getNumberFormat: Ae(function () {
            for (var t, e = [], r = 0; r < arguments.length; r++) e[r] = arguments[r];
            return new ((t = Intl.NumberFormat).bind.apply(t, o([void 0], e, !1)))();
          }, {
            cache: De(a.number),
            strategy: Le.variadic
          }),
          getDateTimeFormat: Ae(function () {
            for (var t, e = [], r = 0; r < arguments.length; r++) e[r] = arguments[r];
            return new ((t = Intl.DateTimeFormat).bind.apply(t, o([void 0], e, !1)))();
          }, {
            cache: De(a.dateTime),
            strategy: Le.variadic
          }),
          getPluralRules: Ae(function () {
            for (var t, e = [], r = 0; r < arguments.length; r++) e[r] = arguments[r];
            return new ((t = Intl.PluralRules).bind.apply(t, o([void 0], e, !1)))();
          }, {
            cache: De(a.pluralRules),
            strategy: Le.variadic
          })
        });
      }
      return Object.defineProperty(t, "defaultLocale", {
        get: function () {
          return t.memoizedDefaultLocale || (t.memoizedDefaultLocale = new Intl.NumberFormat().resolvedOptions().locale), t.memoizedDefaultLocale;
        },
        enumerable: !1,
        configurable: !0
      }), t.memoizedDefaultLocale = null, t.resolveLocale = function (t) {
        if (void 0 !== Intl.Locale) {
          var e = Intl.NumberFormat.supportedLocalesOf(t);
          return e.length > 0 ? new Intl.Locale(e[0]) : new Intl.Locale("string" == typeof t ? t : t[0]);
        }
      }, t.__parse = _e, t.formats = {
        number: {
          integer: {
            maximumFractionDigits: 0
          },
          currency: {
            style: "currency"
          },
          percent: {
            style: "percent"
          }
        },
        date: {
          short: {
            month: "numeric",
            day: "numeric",
            year: "2-digit"
          },
          medium: {
            month: "short",
            day: "numeric",
            year: "numeric"
          },
          long: {
            month: "long",
            day: "numeric",
            year: "numeric"
          },
          full: {
            weekday: "long",
            month: "long",
            day: "numeric",
            year: "numeric"
          }
        },
        time: {
          short: {
            hour: "numeric",
            minute: "numeric"
          },
          medium: {
            hour: "numeric",
            minute: "numeric",
            second: "numeric"
          },
          long: {
            hour: "numeric",
            minute: "numeric",
            second: "numeric",
            timeZoneName: "short"
          },
          full: {
            hour: "numeric",
            minute: "numeric",
            second: "numeric",
            timeZoneName: "short"
          }
        }
      }, t;
    }(),
    Fe = ke,
    Ve = {
      en: _t
    };
  t.BatteryPanel = class extends lt {
    async firstUpdated() {
      window.addEventListener("location-changed", () => {
        window.location.pathname.includes("battery-notes") && this.requestUpdate();
      }), await (async () => {
        if (customElements.get("ha-checkbox") && customElements.get("ha-slider") && !customElements.get("ha-panel-config")) return;
        await customElements.whenDefined("partial-panel-resolver");
        const t = document.createElement("partial-panel-resolver");
        t.hass = {
          panels: [{
            url_path: "tmp",
            component_name: "config"
          }]
        }, t._updateRoutes(), await t.routerOptions.routes.tmp.load(), await customElements.whenDefined("ha-panel-config");
        const e = document.createElement("ha-panel-config");
        await e.routerOptions.routes.automation.load();
      })(), this.requestUpdate();
    }
    render() {
      return V`
      <div class="header">
        <div class="toolbar">
          <ha-menu-button
            .hass=${this.hass}
            .narrow=${this.narrow}
          ></ha-menu-button>
          <div class="main-title">${function (t, e, ...r) {
        const i = e.replace(/['"]+/g, "");
        var n;
        try {
          n = t.split(".").reduce((t, e) => t[e], Ve[i]);
        } catch (e) {
          n = t.split(".").reduce((t, e) => t[e], Ve.en);
        }
        if (void 0 === n && (n = t.split(".").reduce((t, e) => t[e], Ve.en)), !r.length) return n;
        const o = {};
        for (let t = 0; t < r.length; t += 2) {
          let e = r[t];
          e = e.replace(/^{([^}]+)?}$/, "$1"), o[e] = r[t + 1];
        }
        try {
          return new Fe(n, e).format(o);
        } catch (t) {
          return "Translation " + t;
        }
      }("title", this.hass.language)}</div>
        </div>
      </div>
    `;
    }
    static get styles() {
      return u`
      ${ft} :host {
        color: var(--primary-text-color);
        --paper-card-header-color: var(--primary-text-color);
      }
      .header {
        background-color: var(--app-header-background-color);
        color: var(--app-header-text-color, white);
        border-bottom: var(--app-header-border-bottom, none);
      }
      .toolbar {
        height: var(--header-height);
        display: flex;
        align-items: center;
        font-size: 20px;
        padding: 0 16px;
        font-weight: 400;
        box-sizing: border-box;
      }
      .main-title {
        margin: 0 0 0 24px;
        line-height: 20px;
        flex-grow: 1;
      }
      ha-tabs {
        margin-left: max(env(safe-area-inset-left), 24px);
        margin-right: max(env(safe-area-inset-right), 24px);
        --paper-tabs-selection-bar-color: var(
          --app-header-selection-bar-color,
          var(--app-header-text-color, #fff)
        );
        text-transform: uppercase;
      }

      .view {
        height: calc(100vh - 112px);
        display: flex;
        justify-content: center;
      }

      .view > * {
        width: 600px;
        max-width: 600px;
      }

      .view > *:last-child {
        margin-bottom: 20px;
      }

      .version {
        font-size: 14px;
        font-weight: 500;
        color: rgba(var(--rgb-text-primary-color), 0.9);
      }
    `;
    }
  }, n([pt({
    attribute: !1
  })], t.BatteryPanel.prototype, "hass", void 0), n([pt({
    type: Boolean,
    reflect: !0
  })], t.BatteryPanel.prototype, "narrow", void 0), t.BatteryPanel = n([(t => e => "function" == typeof e ? ((t, e) => (customElements.define(t, e), e))(t, e) : ((t, e) => {
    const {
      kind: r,
      elements: i
    } = e;
    return {
      kind: r,
      elements: i,
      finisher(e) {
        customElements.define(t, e);
      }
    };
  })(t, e))("battery-panel")], t.BatteryPanel), Object.defineProperty(t, "__esModule", {
    value: !0
  });
}({});
