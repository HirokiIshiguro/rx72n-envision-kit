/*
* Copyright (c) 2023-2025 Renesas Electronics Corporation and/or its affiliates
*
* SPDX-License-Identifier: BSD-3-Clause
*/

/***********************************************************************************************************************
 * File Name    : code_signer_public_key.h
 * Description  : Header file to define the PEM-encoded code signer public key used for OTA update signature verification.
 **********************************************************************************************************************/

#ifndef CODE_SIGNER_PUBLIC_KEY_H_
#define CODE_SIGNER_PUBLIC_KEY_H_

/*
 * PEM-encoded code signer public key.
 *
 * Must include the PEM header and footer:
 * "-----BEGIN CERTIFICATE-----"\
 * "...base64 data..."\
 * "-----END CERTIFICATE-----"
 */
#define CODE_SIGNER_PUBLIC_KEY_PEM \
"-----BEGIN PUBLIC KEY-----"\
"MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEWiAlaCQGEgIKoP+qk7Uqc/ME/hjw"\
"amq1v/z/LWx15CKig59Pd3+ar2RFOlMMOhIfkYgS+Ha7tH+w0ggnKDrUug=="\
"-----END PUBLIC KEY-----"

#endif /* CODE_SIGNER_PUBLIC_KEY_H_ */
