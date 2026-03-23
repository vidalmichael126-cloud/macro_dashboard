"""views/rules_view.py — Rules & reasoning tab."""
import streamlit as st
from signal_engine import get_full_analysis, STATUS_COLORS


def render():
    analysis = get_full_analysis()
    rules    = analysis.get("rules", [])

    active  = [r for r in rules if r.get("state") == "active"]
    watch   = [r for r in rules if r.get("state") == "watch"]
    rest    = [r for r in rules if r.get("state") not in ("active","watch")]

    st.markdown("### Rules & reasoning")
    st.caption("Every condition shown. Rules only recommend action when evidence supports it.")
    st.divider()

    def _render_rules(rule_list, header):
        if not rule_list:
            return
        st.markdown(f"**{header}**")
        for rule in rule_list:
            state = rule.get("state","watch")
            met   = rule.get("conditions_met",[])
            total = rule.get("conditions_total",0)
            miss  = rule.get("missing",[])
            sev   = rule.get("severity","warning")

            # Header color
            if state == "active":
                bg,border,tc = "#FCEBEB","#E24B4A","#791F1F"
                badge = "ACTIVE"
            elif state == "watch":
                bg,border,tc = "#FAEEDA","#EF9F27","#633806"
                badge = f"WATCH · {len(met)}/{total}"
            else:
                bg,border,tc = "#F1EFE8","#B4B2A9","#5F5E5A"
                badge = "monitoring"

            if sev == "opportunity":
                bg,border,tc = "#E6F1FB","#378ADD","#042C53"

            with st.expander(
                f"{rule['name']}",
                expanded=(state == "active"),
            ):
                st.markdown(
                    f"<div style='background:{bg};border:0.5px solid {border};"
                    f"border-radius:8px;padding:10px 12px;margin-bottom:8px'>"
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center;margin-bottom:5px'>"
                    f"<span style='font-size:13px;font-weight:500;color:{tc}'>{rule['name']}</span>"
                    f"<span style='font-size:10px;font-weight:600;color:{tc};"
                    f"background:rgba(255,255,255,.4);padding:1px 7px;border-radius:3px'>{badge}</span>"
                    f"</div>"
                    f"<div style='font-size:11px;color:{tc};opacity:.85;line-height:1.5'>"
                    f"{rule.get('description','')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Conditions checklist
                conds = rule.get("conditions",{})
                if conds:
                    st.markdown("**Conditions:**")
                    for sig, level in conds.items():
                        is_met = sig in met
                        icon   = "✓" if is_met else "✗"
                        color  = "#27500A" if is_met else "#888"
                        st.markdown(
                            f"<div style='font-size:11px;color:{color};padding:2px 0'>"
                            f"{icon}&nbsp;&nbsp;{sig} ≥ {level}</div>",
                            unsafe_allow_html=True,
                        )

                if rule.get("note"):
                    st.caption(rule["note"])

                # Action — only show if active
                if state == "active" and rule.get("action"):
                    st.markdown(
                        f"<div style='margin-top:8px;padding:7px 10px;"
                        f"background:#E6F1FB;border:0.5px solid #85B7EB;"
                        f"border-radius:6px;font-size:11px;color:#0C447C'>"
                        f"<strong>Action:</strong> {rule['action']}</div>",
                        unsafe_allow_html=True,
                    )
                elif state == "watch" and rule.get("action"):
                    st.markdown(
                        f"<div style='margin-top:8px;padding:7px 10px;"
                        f"background:#F1EFE8;border:0.5px solid #B4B2A9;"
                        f"border-radius:6px;font-size:11px;color:gray;font-style:italic'>"
                        f"When fires: {rule['action']}</div>",
                        unsafe_allow_html=True,
                    )

    _render_rules(active, "Active")
    if watch: st.divider()
    _render_rules(watch,  "Watch — one condition short")
    if rest:  st.divider()
    _render_rules(rest,   "Monitoring")
