/**********************************************************************************************************************
 * File Name    : r_cryptogram.h
 * Description  : Phase 8b 第3次 段階5-4c-2 (rx72n-envision-kit#56) empty stub.
 *                Legacy aws_demos の utility/r_cryptogram.h は SHA1/DES の wrapper API を declare していたが、
 *                v3 baseline 上の firm_update.c は実際にこれら API を呼ばず (SHA256/ECC は tinycrypt 直接、
 *                base64 は r_fwup 内蔵を使用)、include されているだけ。本 stub で include 解決を満たす。
 *********************************************************************************************************************/

#ifndef R_CRYPTOGRAM_H_STUB
#define R_CRYPTOGRAM_H_STUB

/* 中身は空。firm_update.c は本ヘッダから何も使っていない。 */

#endif /* R_CRYPTOGRAM_H_STUB */
