package foundry.authority

default allow := false
default reason := "no authority"

crl_listed if {
  input.auth.serial != null
  input.crl.serials != null
  input.auth.serial in input.crl.serials
}

allow if {
  input.auth.issuer == "arescore-ca"
  not crl_listed
}

reason := "certificate revoked (CRL)" if crl_listed

reason := "unauthorized issuer" if {
  not crl_listed
  input.auth.issuer != "arescore-ca"
}
