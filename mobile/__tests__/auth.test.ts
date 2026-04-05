import * as SecureStore from "expo-secure-store";

import { clearTokens, getStoredTokens, storeTokens } from "../src/lib/auth";
import { AuthTokens } from "../src/lib/auth";

jest.mock("expo-secure-store");

const mockGetItem = SecureStore.getItemAsync as jest.Mock;
const mockSetItem = SecureStore.setItemAsync as jest.Mock;
const mockDeleteItem = SecureStore.deleteItemAsync as jest.Mock;

const SAMPLE_TOKENS: AuthTokens = {
  idToken: "id-token-abc",
  accessToken: "access-token-xyz",
  refreshToken: "refresh-token-123",
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe("getStoredTokens", () => {
  it("returns null when no tokens are stored", async () => {
    mockGetItem.mockResolvedValue(null);
    const result = await getStoredTokens();
    expect(result).toBeNull();
  });

  it("returns null when only idToken is missing", async () => {
    mockGetItem
      .mockResolvedValueOnce(null) // idToken
      .mockResolvedValueOnce("access-token") // accessToken
      .mockResolvedValueOnce("refresh-token"); // refreshToken
    const result = await getStoredTokens();
    expect(result).toBeNull();
  });

  it("returns tokens when all values are stored", async () => {
    mockGetItem
      .mockResolvedValueOnce(SAMPLE_TOKENS.idToken)
      .mockResolvedValueOnce(SAMPLE_TOKENS.accessToken)
      .mockResolvedValueOnce(SAMPLE_TOKENS.refreshToken);
    const result = await getStoredTokens();
    expect(result).toEqual(SAMPLE_TOKENS);
  });

  it("returns null refreshToken when refresh key is absent", async () => {
    mockGetItem
      .mockResolvedValueOnce(SAMPLE_TOKENS.idToken)
      .mockResolvedValueOnce(SAMPLE_TOKENS.accessToken)
      .mockResolvedValueOnce(null);
    const result = await getStoredTokens();
    expect(result).toEqual({ ...SAMPLE_TOKENS, refreshToken: null });
  });
});

describe("storeTokens", () => {
  it("writes idToken, accessToken, and refreshToken to SecureStore", async () => {
    mockSetItem.mockResolvedValue(undefined);
    await storeTokens(SAMPLE_TOKENS);
    expect(mockSetItem).toHaveBeenCalledWith("cognito_id_token", SAMPLE_TOKENS.idToken);
    expect(mockSetItem).toHaveBeenCalledWith("cognito_access_token", SAMPLE_TOKENS.accessToken);
    expect(mockSetItem).toHaveBeenCalledWith("cognito_refresh_token", SAMPLE_TOKENS.refreshToken);
  });

  it("deletes refreshToken key when refreshToken is null", async () => {
    mockSetItem.mockResolvedValue(undefined);
    mockDeleteItem.mockResolvedValue(undefined);
    await storeTokens({ ...SAMPLE_TOKENS, refreshToken: null });
    expect(mockDeleteItem).toHaveBeenCalledWith("cognito_refresh_token");
  });
});

describe("clearTokens", () => {
  it("deletes all three token keys", async () => {
    mockDeleteItem.mockResolvedValue(undefined);
    await clearTokens();
    expect(mockDeleteItem).toHaveBeenCalledWith("cognito_id_token");
    expect(mockDeleteItem).toHaveBeenCalledWith("cognito_access_token");
    expect(mockDeleteItem).toHaveBeenCalledWith("cognito_refresh_token");
  });
});
