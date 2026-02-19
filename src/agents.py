def risk_profile_agent(risk_appetite, horizon):

    if risk_appetite == "low":
        return "Conservative"
    elif risk_appetite == "medium":
        return "Balanced"
    else:
        return "Aggressive"


def amount_filter_agent(df, invest_type, amount):
    # For now keep it simple
    # (Later you can filter SIP min_sip, lumpsum min_lumpsum)
    return df
